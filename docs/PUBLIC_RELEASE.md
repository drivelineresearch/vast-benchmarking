# Public-release checklist

## Prepared through v0.1.1

- The publishable tree passes `scripts/check_public_release.py`.
- The initial public history was reduced to one clean release commit. Later releases use
  ordinary commits with a GitHub noreply author.
- GitHub secret scanning, non-provider pattern scanning, validity checks, push
  protection, dependency alerts, and automated security updates are enabled.
- The wheel and source archive contain no local database, raw result JSON, credential,
  private key, provider log, personal path, or private deployment hostname.
- Git and Docker ignore rules cover credentials, private keys, databases, local editor
  state, caches, build output, and raw results; text and binary normalization is explicit.
- Public documentation is split by purpose, and CI checks every local link.
- Demo claims come from the sanitized 19-run snapshot documented in `reports/`.
- The maintainer's Vast.ai referral link carries a plain disclosure that sign-ups may
  provide account credit and do not influence methodology or rankings.
- CI and the Public safety workflow run on the exact release commit.
- CI builds and scans both distribution formats for expected docs and forbidden private
  material.
- The repository and package metadata use the MIT License under Driveline Research.
- `main` requires current CI and public-safety checks, one approving review, resolved
  conversations, and linear history; force pushes and branch deletion are disabled.
- The v0.1.1 writing pass reviewed every Markdown file and explanatory code comment for
  canned or overly mechanical prose. It did not change benchmark behavior or results.

## Remaining decisions

The [project TODO](TODO.md) tracks the public support policy and whether the hosted demo
should become a supported project feature.
