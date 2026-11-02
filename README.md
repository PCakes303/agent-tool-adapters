# Agent Tool Adapters

**Status:** Experimental reference library deployed in `PCakes303/agent-tool-adapters`; 18 unit tests pass on Python 3.10, 3.11 and 3.12.

A small, dependency-free Python contract for exposing existing tools through consistent, permissioned adapter interfaces. The first vertical slice defines adapter registration, capability declarations, policy-gated invocation, bounded input/output handling, and structured results. It does not ship adapters for specific third-party tools.

## Scope and design

- Adapters are explicitly registered by a trusted application; no dynamic plugin discovery or code loading.
- Every invocation supplies a principal, a declared capability, and a policy decision callback. Missing or denying policy fails closed.
- Adapter identity and declared capabilities are metadata, not proof of identity, safety, or authorization.
- Inputs and outputs are strictly validated against the JSON data model (string object keys only, no tuples, non-finite numbers or cycles) with configurable serialized byte ceilings.
- Calls are synchronous and in-process. Timeouts, process isolation, network authentication, durable audit, and sandbox enforcement belong to upstream/downstream systems.

## Quick start

```python
from agent_tool_adapters import AdapterRegistry, ToolAdapter, Invocation, PolicyDecision

class EchoAdapter:
    adapter_id = "example.echo"
    capabilities = frozenset({"example.echo"})
    def invoke(self, input_data):
        return {"echo": input_data}

registry = AdapterRegistry()
registry.register(EchoAdapter())

def policy(invocation):
    return PolicyDecision(allowed=invocation.capability == "example.echo",
                          decision_id="local-demo")

result = registry.invoke(
    Invocation(principal_id="demo-agent", capability="example.echo",
               input_data={"message": "hello"}, policy=policy)
)
assert result.ok
```

This example demonstrates an injected policy seam only. It does not authenticate `principal_id` or provide a secure execution boundary.

## Contracts

- [Adapter contract](docs/ADAPTER-CONTRACT.md)
- [Threat model and boundaries](docs/THREAT-MODEL.md)
- [JSON Schema](schemas/tool-adapter-descriptor.schema.json)
- [Manifest](manifest.json), [capabilities](capabilities.json), [compatibility](compatibility.json)

## Ecosystem dependencies

Declared prerequisites: AIX Core, Agent Transport Gateway, Agent Policy Engine, and Agent Sandbox Security. These are contract relationships only. The sandbox-security repository is planned and not yet implemented; no sandbox isolation is claimed. Runtime integration with any dependency remains untested.

## Non-goals

No shell execution, arbitrary code loading, credentials storage, network client, third-party tool bundle, container/OS sandbox, authentication, production policy enforcement, or production-ready security claim.

## Validation

```bash
python -m unittest discover -s tests -v
```

Python 3.10–3.12 CI passes all 18 unit tests. Licensing remains pending portfolio-level review; no license is asserted.
