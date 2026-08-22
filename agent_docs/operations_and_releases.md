# Operations and releases

Read this before touching Vast rentals, a deployed dashboard service, or release metadata.

## Vast operations

- Resolve an offer again immediately before creating an instance. Enforce hourly and
  projected-cost limits against the SQLite rental ledger.
- Refuse ambiguous cleanup. Destroy only the exact instance created by the current run,
  then verify it is absent.
- Attach only the public SSH key. Provider credentials stay on the controller.
- Keep provisioning failures and partial benchmark attempts as annotations or excluded
  records. Do not turn them into performance claims.

## Dashboard deployment

- Keep production hostnames, account names, ports, and filesystem details out of tracked
  documentation. Use `docs/self-hosting.md` for the portable deployment contract.
- Inspect the target host's service and proxy configuration before deploying. Do not
  replace it blindly with a tracked example.
- A dashboard-only deployment must preserve the durable SQLite database and must not
  operate on Vast workers or rentals.
- Verify loopback and external `/healthz`, representative HTML, and required static
  assets after a restart. A first probe can race Gunicorn startup, so confirm service
  state and retry before declaring failure.

## Release workflow

- Keep `pyproject.toml` and `src/vast_benchmarking/__init__.py` versions synchronized.
- Update `CHANGELOG.md`, run the full root verification gate, and build with `uv build`.
- Inspect wheel and source archive contents before tagging.
- Use an annotated `v<version>` tag and attach both distributions to the GitHub release.
- Publishing to a package registry or rewriting history requires separate owner
  approval. Repository visibility and license changes also need owner approval unless
  the current task explicitly includes them.
