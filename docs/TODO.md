# Project TODO

Release packaging and repository safeguards are in place. A few policy and hosting
decisions are still open.

## Owner decisions

- [x] Choose and add an open-source license: MIT.
- [ ] Choose the support policy for public issues and discussions.
- [x] Configure `main` branch protection and required checks.
- [x] Make the repository public after the v0.1.1 release checks pass.

## Documentation follow-up

- [ ] Decide whether a public hosted demo should be supported as a project feature.
- [ ] If so, publish only a generic deployment recipe and public URL. Keep private
  hostnames, account names, ports, and host-specific service details in untracked
  operator documentation.

## Completed preparation

- [x] Removed private production-service details and live infrastructure URLs from
  public documentation.
- [x] Split the demo, methodology, Vast runner, and self-hosting material into focused
  guides.
- [x] Added public-safety, dependency, package-content, and documentation-link checks.
- [x] Added the MIT License and package metadata.
- [x] Protected `main` with strict CI checks, one approval, stale-review dismissal,
  conversation resolution, linear history, and force-push/deletion prevention.
- [x] Rewrote the repository to one sanitized public-release commit.
- [x] Edited all Markdown and explanatory code comments with the humanizer review.
