# Contributing

Use Python 3.10 or newer and keep benchmark changes bounded by the existing wall-clock
budget. Before opening a pull request:

```bash
uv sync --extra dev
uv run ruff check src tests
uv run pytest
uv run python scripts/check_public_release.py
```

Do not commit provider credentials, SSH private keys, local databases, raw rented-host
results, personal filesystem paths, or private infrastructure addresses. Add synthetic
fixtures when a test needs machine metadata.

Performance changes should document the profile, hardware scope, metric units, and any
acceptance-rule change. Marketplace price is historical context captured at run time,
not a current quote.
