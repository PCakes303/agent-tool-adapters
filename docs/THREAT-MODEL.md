# Threat Model

## Assets

Tool credentials and data held by the host, invocation inputs/outputs, principal context, policy decisions, and integrity of adapter registration.

## Trust boundaries

The registry trusts the host to authenticate the principal, register reviewed adapter objects, supply a trustworthy policy callback, and execute inside an appropriate isolation boundary. Adapter code is trusted code in this prototype.

## Threats and mitigations

- **Unauthorized invocation:** every call requires a policy callback; missing, denying, or failing decisions deny invocation. This is only a local seam, not a production authorization service.
- **Capability confusion:** exact capability identifiers are matched; no wildcard behavior is provided.
- **Payload exhaustion:** Strict JSON data-model validation, configurable byte limits, and a configurable nesting-depth ceiling (64 by default) bound payload shape and size. This does not bound CPU, memory, recursion during adapter execution, or execution time.
- **Adapter exceptions:** exceptions are converted to generic result codes rather than returned verbatim.
- **Malicious adapter code:** not mitigated. Adapters execute in-process with host privileges.
- **Identity spoofing:** not mitigated. Principal IDs are caller-provided values unless the host authenticates them.
- **Network attacks and replay:** outside scope; no network protocol or replay store exists.

## Required before production use

Authenticated identity and transport, policy engine integration, process/container/OS isolation, resource quotas, timeouts and cancellation, secret brokering, durable audit, supply-chain verification, adversarial tests, and a security review. The planned sandbox-security dependency is not implemented and must not be represented as an existing control.
