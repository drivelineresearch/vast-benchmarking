# Changelog

All notable changes to this project are documented here.

## 0.1.0 - 2026-08-22

### Added

- Bounded GPU, CPU, memory, and disk benchmark profiles with portable JSON results.
- Safe single-offer and parallel Vast runners with projected-cost enforcement and exact
  instance cleanup.
- SQLite-backed Flask dashboard with six category leaderboards, machine annotations,
  percent-of-best bars, historical price context, and performance-per-dollar sorting.
- Sanitized demo results from 19 stored runs, including 15 accepted machines and 60 GPUs.
- Public-release scanner, contributor and security guidance, deployment examples, and
  project instructions for Claude Code and other coding agents.
- A professional light dashboard theme with self-hosted Geist Sans and Geist Mono.
- Generated dashboard artwork and favicon family.
- Modular public documentation with a separate measured demo, methodology, Vast runner,
  and generic self-hosting guides.
- Editor, Git, Docker, dependency-update, and Markdown-link checks for public maintenance.
- A disclosed optional Vast.ai referral link that does not influence benchmark results.

### Safety

- API credentials and private SSH keys remain controller-only and are excluded from
  repository artifacts.
- Partial GPU runs and superseded machine/category runs remain auditable but do not enter
  leaderboards.
