# Agent entrypoint

Read `CLAUDE.md` completely before modifying this repository. It is the authoritative
WHAT/WHY/HOW guide for all coding agents.

Load only the focused document needed for the task:

- Benchmark semantics: `agent_docs/benchmark_contract.md`
- Rentals, deployment, and releases: `agent_docs/operations_and_releases.md`
- Public repository preparation: `docs/PUBLIC_RELEASE.md`

Always preserve untracked results and the live SQLite database. Paid Vast rentals,
repository visibility changes, and Git history rewrites require explicit user approval.
