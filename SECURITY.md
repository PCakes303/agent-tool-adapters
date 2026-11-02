# Security Policy

This repository is an experimental in-process adapter registry and policy-gating seam. It does not authenticate principals, enforce production authorization, isolate adapter code, limit execution time, or protect credentials.

- Register only reviewed adapter objects.
- Never expose the registry directly to untrusted callers.
- Supply a trusted policy decision function and authenticated principal context from the host.
- Execute untrusted or blocking adapters only behind a separately verified sandbox with resource limits and timeouts.
- Treat all adapter inputs and outputs as untrusted data; enforce byte-size, nesting-depth and total-item ceilings before and after adapter invocation.
- Adapter identifiers, capability sets, principal identifiers and policy decision identifiers are length/count bounded. Malformed direct invocation objects fail closed.
- Do not place credentials, tokens, private data, or secrets in this repository.

## Vulnerability reporting

Do not publish exploitable vulnerability details in public issues. Use GitHub private vulnerability reporting or a private security advisory only if enabled for this repository. No dedicated private reporting address is published here; if GitHub private reporting is unavailable, the owner must configure an approved private reporting channel before production use. Do not send credentials, tokens, or sensitive operational data through public channels.
