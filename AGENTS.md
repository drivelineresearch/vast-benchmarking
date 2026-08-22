# Agent entrypoint

Read `CLAUDE.md` completely before modifying this repository. It explains what the
project does, why its constraints exist, and how to work here safely.

Load only the focused document needed for the task:

- Benchmark semantics: `agent_docs/benchmark_contract.md`
- Rentals, deployment, and releases: `agent_docs/operations_and_releases.md`
- Public repository preparation: `docs/PUBLIC_RELEASE.md`

Preserve untracked results and the live SQLite database. Get explicit user approval
before starting a paid Vast rental, changing repository visibility, or rewriting Git
history.
