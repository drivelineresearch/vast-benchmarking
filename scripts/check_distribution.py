#!/usr/bin/env python3
"""Inspect built wheel and source archives for public-release mistakes."""

from __future__ import annotations

import argparse
import tarfile
import zipfile
from pathlib import Path

from check_public_release import RULES

EXPECTED_SDIST = {
    "LICENSE",
    "docs/benchmarks/2026-08-22-demo.md",
    "docs/benchmark-methodology.md",
    "docs/running-on-vast.md",
    "docs/self-hosting.md",
    "scripts/check_distribution.py",
    "scripts/check_markdown_links.py",
    "scripts/check_public_release.py",
}
EXPECTED_WHEEL = {
    "vast_benchmarking/static/favicon.ico",
    "vast_benchmarking/static/fonts/Geist-Variable.woff2",
    "vast_benchmarking/static/vast-benchmarking-header-v2.png",
}
FORBIDDEN_PARTS = {".git", ".github", ".venv", "__pycache__", "results"}
FORBIDDEN_SUFFIXES = {".db", ".key", ".pem", ".sqlite", ".sqlite3"}


def read_wheel(path: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(path) as archive:
        return {name: archive.read(name) for name in archive.namelist() if not name.endswith("/")}


def read_sdist(path: Path) -> dict[str, bytes]:
    with tarfile.open(path, "r:gz") as archive:
        files = [member for member in archive.getmembers() if member.isfile()]
        prefix = files[0].name.split("/", 1)[0]
        return {
            member.name.removeprefix(f"{prefix}/"): archive.extractfile(member).read()
            for member in files
        }


def inspect_entries(path: Path, entries: dict[str, bytes], expected: set[str]) -> list[str]:
    findings: list[str] = []
    missing = expected - entries.keys()
    findings.extend(f"{path}: missing expected file {name}" for name in sorted(missing))

    for name, data in entries.items():
        archive_path = Path(name)
        if any(part in FORBIDDEN_PARTS for part in archive_path.parts):
            findings.append(f"{path}: forbidden path {name}")
        if archive_path.suffix.lower() in FORBIDDEN_SUFFIXES:
            findings.append(f"{path}: forbidden file type {name}")
        if archive_path.name.startswith(".env") and archive_path.name != ".env.example":
            findings.append(f"{path}: forbidden environment file {name}")
        if b"\0" in data[:8192]:
            continue
        for label, pattern in RULES.items():
            for match in pattern.finditer(data):
                if label == "email address" and match.group(0).endswith(
                    b"@users.noreply.github.com"
                ):
                    continue
                line = data.count(b"\n", 0, match.start()) + 1
                findings.append(f"{path}:{name}:{line}: {label}")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dist", type=Path, default=Path("dist"))
    args = parser.parse_args()

    wheels = sorted(args.dist.glob("*.whl"))
    sdists = sorted(args.dist.glob("*.tar.gz"))
    findings: list[str] = []
    if len(wheels) != 1:
        findings.append(f"expected one wheel in {args.dist}, found {len(wheels)}")
    if len(sdists) != 1:
        findings.append(f"expected one source archive in {args.dist}, found {len(sdists)}")
    for wheel in wheels:
        entries = read_wheel(wheel)
        findings.extend(inspect_entries(wheel, entries, EXPECTED_WHEEL))
        if not any(name.endswith(".dist-info/licenses/LICENSE") for name in entries):
            findings.append(f"{wheel}: missing packaged MIT license")
    for sdist in sdists:
        findings.extend(inspect_entries(sdist, read_sdist(sdist), EXPECTED_SDIST))

    if findings:
        print("Distribution check failed:")
        print("\n".join(findings))
        return 1
    print(f"Distribution check passed for {len(wheels) + len(sdists)} artifacts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
