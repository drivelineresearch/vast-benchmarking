# Documentation

Pick the shortest guide that matches what you are trying to do.

## 🚀 Get started

- [Project overview](../README.md): install, run a local smoke test, and open the dashboard.
- [Running on Vast.ai](running-on-vast.md): safely benchmark one offer or a bounded batch.
- [Self-hosting](self-hosting.md): serve a SQLite result database with Gunicorn and a
  reverse proxy.

## 📊 Understand the results

- [Demo benchmark snapshot](benchmarks/2026-08-22-demo.md): measured leaders, machine
  IDs, historical rates, campaign cost, and exclusions.
- [Benchmark methodology](benchmark-methodology.md): workloads, units, effective cores,
  acceptance rules, rankings, and caveats.
- [Expansion campaign report](../reports/2026-08-22-expansion-results.md): the complete
  sanitized campaign table and unsuccessful attempts.

## 🧰 Maintain the project

- [Contributing](../CONTRIBUTING.md): development environment and pull-request checks.
- [Security](../SECURITY.md): vulnerability reporting and credential boundaries.
- [Public-release checklist](PUBLIC_RELEASE.md): completed controls and owner decisions.
- [Public-release TODO](TODO.md): remaining organization and visibility decisions.
- [Changelog](../CHANGELOG.md): user-visible changes by release.
- [v0.1.0 release notes](releases/v0.1.0.md): packaged release contents.

## 🤖 Coding-agent context

- [Repository guide](../CLAUDE.md): the short WHAT, WHY, and HOW map.
- [Benchmark contract](../agent_docs/benchmark_contract.md): invariants for execution,
  validation, storage, and scoring changes.
- [Operations and releases](../agent_docs/operations_and_releases.md): paid-compute,
  deployment, and release guardrails.
