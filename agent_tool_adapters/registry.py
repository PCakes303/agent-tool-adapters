"""Explicit registry and fail-closed invocation boundary.

This is an in-process API seam, not a sandbox or authenticated enforcement point.
"""
from __future__ import annotations
import json
import math
from typing import Any, Protocol, runtime_checkable
from .models import Invocation, InvocationResult, PolicyDecision

class AdapterError(Exception):
    """Base exception for expected adapter registry errors."""

class AdapterProtocolError(AdapterError):
    """An adapter does not satisfy the minimal adapter contract."""

@runtime_checkable
class ToolAdapter(Protocol):
    adapter_id: str
    capabilities: frozenset[str]
    def invoke(self, input_data: Any) -> Any: ...

class AdapterRegistry:
    def __init__(self, *, max_payload_bytes: int = 1_048_576) -> None:
        if not isinstance(max_payload_bytes, int) or isinstance(max_payload_bytes, bool) or max_payload_bytes < 1:
            raise ValueError("max_payload_bytes must be a positive integer")
        self._max_payload_bytes = max_payload_bytes
        self._adapters: dict[str, ToolAdapter] = {}
        self._capabilities: dict[str, frozenset[str]] = {}

    def register(self, adapter: ToolAdapter) -> None:
        adapter_id = getattr(adapter, "adapter_id", None)
        capabilities = getattr(adapter, "capabilities", None)
        invoke = getattr(adapter, "invoke", None)
        if not isinstance(adapter_id, str) or not adapter_id.strip():
            raise AdapterProtocolError("adapter_id must be a non-empty string")
        if not isinstance(capabilities, (set, frozenset)) or not capabilities:
            raise AdapterProtocolError("capabilities must be a non-empty set")
        if any(not isinstance(c, str) or not c.strip() for c in capabilities):
            raise AdapterProtocolError("capabilities must contain non-empty strings")
        if not callable(invoke):
            raise AdapterProtocolError("adapter must provide callable invoke(input_data)")
        if adapter_id in self._adapters:
            raise AdapterError(f"adapter already registered: {adapter_id}")
        normalized = frozenset(capabilities)
        collisions = {cap for cap in normalized
                      if any(cap in existing for existing in self._capabilities.values())}
        if collisions:
            raise AdapterError("capability already registered: " + ", ".join(sorted(collisions)))
        self._adapters[adapter_id] = adapter
        self._capabilities[adapter_id] = normalized

    def descriptors(self) -> list[dict[str, Any]]:
        return [{"adapter_id": key, "capabilities": sorted(self._capabilities[key])}
                for key, value in sorted(self._adapters.items())]

    def invoke(self, invocation: Invocation) -> InvocationResult:
        if not isinstance(invocation.principal_id, str) or not invocation.principal_id.strip():
            return self._denied("unknown", invocation.capability, "invalid_principal")
        if not isinstance(invocation.capability, str) or not invocation.capability.strip():
            return self._denied("unknown", "", "invalid_capability")
        matches = [(key, adapter) for key, adapter in self._adapters.items()
                   if invocation.capability in self._capabilities[key]]
        if len(matches) != 1:
            return self._denied(matches[0][0] if matches else "unknown",
                                invocation.capability, "capability_not_registered")
        adapter_id, adapter = matches[0]
        try:
            self._check_payload(invocation.input_data)
        except (TypeError, ValueError, OverflowError, RecursionError):
            return self._denied(adapter_id, invocation.capability, "invalid_or_oversized_input")
        try:
            decision = invocation.policy(invocation)
        except Exception:
            return self._denied(adapter_id, invocation.capability, "policy_error")
        if not isinstance(decision, PolicyDecision) or decision.allowed is not True:
            decision_id = decision.decision_id if isinstance(decision, PolicyDecision) else None
            return self._denied(adapter_id, invocation.capability, "policy_denied",
                                decision_id)
        try:
            output = adapter.invoke(invocation.input_data)
            self._check_payload(output)
        except (TypeError, ValueError, OverflowError):
            return self._denied(adapter_id, invocation.capability, "invalid_or_oversized_output",
                                decision.decision_id)
        except Exception:
            return self._denied(adapter_id, invocation.capability, "adapter_error",
                                getattr(decision, "decision_id", None))
        return InvocationResult(True, adapter_id, invocation.capability, output=output,
                                decision_id=getattr(decision, "decision_id", None))

    def _check_payload(self, value: Any) -> None:
        # Accept only the JSON data model (not Python's tuple or non-string-key
        # coercions), and reject cycles before serialization.
        active: set[int] = set()
        stack = [(value, False)]
        while stack:
            item, exiting = stack.pop()
            if isinstance(item, (dict, list)):
                marker = id(item)
                if exiting:
                    active.remove(marker)
                    continue
                if marker in active:
                    raise ValueError("cyclic payload is not JSON-compatible")
                active.add(marker)
                stack.append((item, True))
                if isinstance(item, dict):
                    if any(not isinstance(key, str) for key in item):
                        raise TypeError("JSON object keys must be strings")
                    stack.extend((child, False) for child in item.values())
                else:
                    stack.extend((child, False) for child in item)
            elif item is None or isinstance(item, (str, bool, int)):
                continue
            elif isinstance(item, float):
                if not math.isfinite(item):
                    raise ValueError("non-finite numbers are not valid JSON")
            else:
                raise TypeError("payload contains a non-JSON value")
        try:
            encoded = json.dumps(value, ensure_ascii=False, allow_nan=False,
                                 separators=(",", ":")).encode("utf-8")
        except (TypeError, ValueError, OverflowError, RecursionError) as exc:
            raise ValueError("payload is not safely serializable as JSON") from exc
        if len(encoded) > self._max_payload_bytes:
            raise ValueError("payload exceeds configured byte limit")

    @staticmethod
    def _denied(adapter_id: str, capability: str, code: str,
                decision_id: str | None = None) -> InvocationResult:
        return InvocationResult(False, adapter_id, capability, error_code=code,
                                error_message="Invocation was not completed.",
                                decision_id=decision_id)
