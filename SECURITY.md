# Security policy

Report suspected credential exposure or a destructive rental-runner bug through
GitHub's private security advisory flow. Never put API keys, SSH material, rented-host
addresses, or account details in a public issue.

Keep the Vast API key on the controller. Remote benchmark containers receive source
code and a temporary public-key attachment, but never the provider credential.

Supported security fixes target the current `main` branch.
