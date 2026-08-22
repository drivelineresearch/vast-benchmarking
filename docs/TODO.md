# 📋 Public-release TODO

The repository contents and package artifacts are prepared. These remaining items need
an owner or organization-level decision before changing GitHub visibility.

## Owner decisions

- [ ] Choose and add an open-source license.
- [ ] Choose the support policy for public issues and discussions.
- [ ] Configure `main` branch protection and required checks.
- [ ] Change repository visibility only after the release workflows pass on the final
  commit.

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
- [x] Rewrote the repository to one sanitized public-release commit.
