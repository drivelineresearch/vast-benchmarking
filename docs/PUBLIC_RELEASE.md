# Public-release checklist

## Prepared in v0.1.0

- The publishable tree passes `scripts/check_public_release.py`.
- Git history is a single sanitized public-release commit with a GitHub noreply author.
- GitHub secret scanning, non-provider pattern scanning, validity checks, push
  protection, dependency alerts, and automated security updates are enabled.
- The wheel and source archive contain no local database, raw result JSON, credential,
  private key, provider log, personal path, or private deployment hostname.
- Git and Docker ignore rules cover credentials, private keys, databases, local editor
  state, caches, build output, and raw results; text and binary normalization is explicit.
- Public documentation is split into user, methodology, demo, hosting, maintainer, and
  coding-agent guides, with local links checked in CI.
- Demo claims come from the sanitized 19-run snapshot documented in `reports/`.
- The maintainer's Vast.ai referral link carries a plain disclosure that sign-ups may
  provide account credit and do not influence methodology or rankings.
- CI and the Public safety workflow run on the exact release commit.
- CI builds and scans both distribution formats for expected docs and forbidden private
  material.
- The repository and package metadata use the MIT License under Driveline Research.
- `main` requires current CI and public-safety checks, one approving review, resolved
  conversations, and linear history; force pushes and branch deletion are disabled.

## Owner decisions before changing visibility

See the [public-release TODO](TODO.md) for the remaining support, hosted-demo, and
visibility decisions.
