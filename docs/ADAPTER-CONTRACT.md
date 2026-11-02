# Tool Adapter Contract (experimental 0.1.0)

## Responsibilities

An adapter wraps one existing tool behind a stable `adapter_id`, a finite set of capability identifiers, and an `invoke(input_data)` method. The host owns registration, policy evaluation, identity authentication, transport, sandboxing, timeouts, cancellation, and audit persistence.

## Invocation sequence

1. A trusted host constructs an invocation using an authenticated principal context.
2. The host selects a registered adapter by exact capability identifier.
3. The registry calls the injected policy callback for that invocation. Missing, exceptional, or denying policy results fail closed.
4. Input is validated as JSON-compatible and constrained by a serialized UTF-8 byte ceiling and a configurable maximum nesting depth (64 by default).
5. The adapter is called in-process. Its output is subjected to the same JSON and size constraints.
6. A structured result reports success or a non-sensitive error code and the policy decision identifier.

## Adapter requirements

- IDs and capability names are stable, non-empty identifiers.
- No implicit wildcard capability matching.
- No automatic import, package installation, discovery, or execution of adapter code.
- Adapters must not treat input as trusted, and must not return secrets in errors.
- Hosts must apply timeouts and isolation outside this library before using untrusted or blocking adapters.

## Future AIX and transport mapping

AIX task intent/capability semantics may be mapped into this invocation envelope by a separately versioned integration profile. Transport Gateway may carry requests to a host, but this library does not implement that integration. Do not mark either dependency tested until cross-repository conformance fixtures exist.
