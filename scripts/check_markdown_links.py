#!/usr/bin/env python3
"""Fail when a local link in a publishable Markdown file has no target."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlsplit

MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\((?P<target>[^)]+)\)")
HTML_LINK = re.compile(r"(?:href|src)=[\"'](?P<target>[^\"']+)[\"']")
REMOTE_SCHEMES = {"http", "https", "mailto"}


def tracked_markdown() -> list[Path]:
    output = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "*.md", "*.mdx"]
    )
    return [Path(line) for line in output.decode().splitlines() if line]


def local_target(source: Path, raw_target: str) -> Path | None:
    target = raw_target.strip().split(maxsplit=1)[0].strip("<>")
    parsed = urlsplit(target)
    if not parsed.path or parsed.scheme.lower() in REMOTE_SCHEMES or target.startswith("#"):
        return None
    path = Path(unquote(parsed.path))
    return path.relative_to("/") if path.is_absolute() else source.parent / path


def main() -> int:
    missing: list[str] = []
    for source in tracked_markdown():
        body = source.read_text(encoding="utf-8")
        for line_number, line in enumerate(body.splitlines(), start=1):
            matches = [*MARKDOWN_LINK.finditer(line), *HTML_LINK.finditer(line)]
            for match in matches:
                target = local_target(source, match.group("target"))
                if target is not None and not target.resolve().exists():
                    missing.append(f"{source}:{line_number}: missing {target}")

    if missing:
        print("Markdown link check failed:")
        print("\n".join(missing))
        return 1
    print(f"Markdown link check passed for {len(tracked_markdown())} files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
