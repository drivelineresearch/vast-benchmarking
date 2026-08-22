# Vast Benchmarking

## Why this project exists

Vast Benchmarking measures how much hardware a rented Docker container can actually
use. The tests cover CV-heavy multi-GPU work, effective CPU concurrency, single-thread
CPU speed, memory bandwidth, and durable disk throughput. Runs stay bounded and
auditable because provider time costs money and listed specifications do not always
match the capacity exposed to a container.

## What is in the repository

- `src/vast_benchmarking/`: Python package, CLI entrypoints, benchmark implementation,
  Vast orchestration, SQLite storage, scoring, and Flask dashboard.
- `tests/`: synthetic unit and integration tests. Never depend on a live rental here.
- `manifests/`: historical, bounded Vast campaign inputs.
- `reports/`: sanitized campaign summaries and machine annotations.
- `deploy/`: portable systemd and Apache examples. The tracked service file is not the
  host's live unit.
- `scripts/`: result maintenance and public-release checks.
- `docs/`: user, methodology, self-hosting, benchmark snapshot, and release guides.
- `agent_docs/`: task-specific contracts that should be loaded only when relevant.

The portable JSON result is the source record. SQLite normalizes that record for the
dashboard while retaining the raw payload.

## How to work here

Use Python 3.10 or newer and `uv` for the environment and package commands.

Before changing code, inspect `git status` and preserve unrelated work. Before handing
off a change, run:

```bash
uv run ruff check src tests scripts
uv run pytest
node --check src/vast_benchmarking/static/app.js
uv run python scripts/check_markdown_links.py
uv run python scripts/check_public_release.py
uv build
uv run python scripts/check_distribution.py
```

Use synthetic fixtures for tests. If a dashboard change affects reverse-proxy behavior,
verify both ordinary Flask links and links under a configured path prefix.

Read the focused docs before these task types:

- Benchmark, scoring, acceptance, or schema changes: `agent_docs/benchmark_contract.md`
- Vast rentals, live deployment, versioning, or releases:
  `agent_docs/operations_and_releases.md`
- User-facing execution or deployment instructions: `docs/running-on-vast.md` and
  `docs/self-hosting.md`
- Repository visibility changes: `docs/PUBLIC_RELEASE.md`

## Rules that must not change

- Never start a paid Vast rental unless the user explicitly authorizes that rental or
  campaign and its cost ceiling.
- Treat the requested cost ceiling and the benchmark wall-clock ceiling as hard limits.
- Never send the Vast API key or an SSH private key to a rented machine.
- Never commit `.env`, SQLite databases, raw result JSON, provider logs, or private keys.
- Effective CPU means the lower of container affinity and cgroup quota. Do not substitute
  a marketplace host-core count.
- Partial GPU runs do not enter leaderboards. Every visible GPU worker must return.
- Rental prices are historical observations captured at run time, not current quotes.
- Preserve the live results database when deploying dashboard code.
- Repository history rewriting and visibility changes require explicit owner approval.

<!-- AGENT-MANAGED SECTION -->
<!-- Agents may add short, broadly useful findings below this line. -->

## Discovered patterns

- `ProxyFix` supplies the external host, scheme, and optional path prefix from a trusted
  loopback reverse proxy.
- Category bars always represent raw performance as percent of the fastest accepted run,
  even when the browser reorders rows by performance per dollar.
