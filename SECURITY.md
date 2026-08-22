# Security policy

Please report suspected credential exposure or a destructive rental-runner issue through
GitHub's private security advisory flow. Do not open a public issue containing API keys,
SSH material, rented-host addresses, or account details.

The Vast API key belongs only on the controller. Remote benchmark containers receive
source code and a temporary public-key attachment, never the provider credential.

Supported security fixes target the current `main` branch.
