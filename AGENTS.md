# Agent instructions

Keep adapter registration explicit and deterministic. Preserve default-deny behavior and exact capability matching. Never treat principal IDs, adapter descriptors, or capability declarations as authentication or proof of safety. Do not add shell execution, dynamic imports, automatic package installation, or implicit network access. Add regression tests for every authorization and payload boundary. Clearly distinguish declared dependencies from tested integrations. This package is not a sandbox.
