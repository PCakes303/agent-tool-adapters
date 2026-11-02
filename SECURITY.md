# Security

This repository is an experimental in-process adapter registry and policy-gating seam. It does not authenticate principals, enforce production authorization, isolate adapter code, limit execution time, or protect credentials.

- Register only reviewed adapter objects.
- Never expose the registry directly to untrusted callers.
- Supply a trusted policy decision function and authenticated principal context from the host.
- Execute untrusted or blocking adapters only behind a separately verified sandbox with resource limits and timeouts.
- Treat all adapter inputs and outputs as untrusted data.
- Do not place credentials, tokens, private data, or secrets in this repository.

Report vulnerabilities through GitHub's private vulnerability reporting if enabled; otherwise contact the repository owner privately. Do not publish exploit details before coordinated remediation.
