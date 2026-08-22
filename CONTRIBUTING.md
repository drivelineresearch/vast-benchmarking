# Contributing

Use Python 3.10 or newer and keep benchmark changes bounded by the existing wall-clock
budget. Before opening a pull request:

```bash
uv sync --extra dev --extra server
uv run ruff check src tests scripts
uv run pytest
node --check src/vast_benchmarking/static/app.js
uv run python scripts/check_markdown_links.py
uv run python scripts/check_public_release.py
uv build
uv run python scripts/check_distribution.py
```

Do not commit provider credentials, SSH private keys, local databases, raw rented-host
results, personal filesystem paths, or private infrastructure addresses. Add synthetic
fixtures when a test needs machine metadata.

Performance changes should document the profile, hardware scope, metric units, and any
acceptance-rule change. Marketplace price is historical context captured at run time,
not a current quote.

## Documentation

Keep the root README short. Measured snapshots belong in `docs/benchmarks/`; user and
operator guides go in `docs/`. Put durable coding-agent contracts in `agent_docs/` and
generated campaign evidence in `reports/`.

Use descriptive link text and run the local-link check before opening a pull request.
