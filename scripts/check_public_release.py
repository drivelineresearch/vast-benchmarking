#!/usr/bin/env python3
"""Fail when publishable repository files contain common secret or PII patterns."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

RULES = {
    "absolute user home path": re.compile(rb"(?:/home|/Users)/[A-Za-z0-9._-]+/"),
    "private key material": re.compile(rb"BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY"),
    "non-empty secret assignment": re.compile(
        rb"(?m)^\s*(?:export\s+)?(?:VAST_API_KEY|API_KEY|ACCESS_TOKEN|SECRET|PASSWORD)"
        rb"\s*[:=]\s*['\"]?[^\s'\"#]{8,}"
    ),
    "email address": re.compile(rb"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b"),
}


def repository_files() -> list[Path]:
    output = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"]
    )
    return [Path(item.decode()) for item in output.split(b"\0") if item]


def main() -> int:
    findings: list[str] = []
    for path in repository_files():
        if not path.is_file():
            continue
        data = path.read_bytes()
        if b"\0" in data[:8192]:
            continue
        for label, pattern in RULES.items():
            for match in pattern.finditer(data):
                if label == "email address" and match.group(0).endswith(
                    b"@users.noreply.github.com"
                ):
                    continue
                line = data.count(b"\n", 0, match.start()) + 1
                findings.append(f"{path}:{line}: {label}")

    if findings:
        print("Public-release check failed:")
        print("\n".join(findings))
        return 1
    print(f"Public-release check passed for {len(repository_files())} repository files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
