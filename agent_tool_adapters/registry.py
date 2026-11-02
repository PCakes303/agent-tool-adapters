"""Explicit registry and fail-closed invocation boundary.

This is an in-process API seam, not a sandbox or authenticated enforcement point.
"""
from __future__ import annotations
import json
import math
import re
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

_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
MAX_ADAPTERS = 10_000
MAX_CAPABILITIES_PER_ADAPTER = 128
MAX_PAYLOAD_BYTES = 64 * 1024 * 1024
MAX_PAYLOAD_DEPTH = 256
MAX_PAYLOAD_ITEMS = 100_000


class AdapterRegistry:
    def __init__(
        self,
        *,
        max_payload_bytes: int = 1_048_576,
        max_payload_depth: int = 64,
        max_payload_items: int = 100_000,
    ) -> None:
        if not isinstance(max_payload_bytes, int) or isinstance(max_payload_bytes, bool) or not 1 <= max_payload_bytes <= MAX_PAYLOAD_BYTES:
            raise ValueError(f"max_payload_bytes must be an integer in [1, {MAX_PAYLOAD_BYTES}]")
        if not isinstance(max_payload_depth, int) or isinstance(max_payload_depth, bool) or not 1 <= max_payload_depth <= MAX_PAYLOAD_DEPTH:
            raise ValueError(f"max_payload_depth must be an integer in [1, {MAX_PAYLOAD_DEPTH}]")
        if not isinstance(max_payload_items, int) or isinstance(max_payload_items, bool) or not 1 <= max_payload_items <= MAX_PAYLOAD_ITEMS:
            raise ValueError(f"max_payload_items must be an integer in [1, {MAX_PAYLOAD_ITEMS}]")
        self._max_payload_bytes = max_payload_bytes
        self._max_payload_depth = max_payload_depth
        self._max_payload_items = max_payload_items
        self._adapters: dict[str, ToolAdapter] = {}
        self._capabilities: dict[str, frozenset[str]] = {}

    def register(self, adapter: ToolAdapter) -> None:
        adapter_id = getattr(adapter, "adapter_id", None)
        capabilities = getattr(adapter, "capabilities", None)
        invoke = getattr(adapter, "invoke", None)
        if not isinstance(adapter_id, str) or not _IDENTIFIER.fullmatch(adapter_id):
            raise AdapterProtocolError("adapter_id must be a bounded identifier")
        if not isinstance(capabilities, (set, frozenset)) or not 1 <= len(capabilities) <= MAX_CAPABILITIES_PER_ADAPTER:
            raise AdapterProtocolError(f"capabilities must be a set of 1..{MAX_CAPABILITIES_PER_ADAPTER} identifiers")
        if any(not isinstance(c, str) or not _IDENTIFIER.fullmatch(c) for c in capabilities):
            raise AdapterProtocolError("capabilities must contain bounded identifiers")
        if not callable(invoke):
            raise AdapterProtocolError("adapter must provide callable invoke(input_data)")
        if adapter_id in self._adapters:
            raise AdapterError(f"adapter already registered: {adapter_id}")
        if len(self._adapters) >= MAX_ADAPTERS:
            raise AdapterError("adapter registry capacity reached")
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
        if not isinstance(invocation, Invocation):
            return self._denied("unknown", "", "invalid_invocation")
        if not isinstance(invocation.capability, str) or not _IDENTIFIER.fullmatch(invocation.capability):
            return self._denied("unknown", "", "invalid_capability")
        if not isinstance(invocation.principal_id, str) or not _IDENTIFIER.fullmatch(invocation.principal_id):
            return self._denied("unknown", invocation.capability, "invalid_principal")
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
        if not callable(invocation.policy):
            return self._denied(adapter_id, invocation.capability, "policy_unavailable")
        try:
            decision = invocation.policy(invocation)
        except Exception:
            return self._denied(adapter_id, invocation.capability, "policy_error")
        if not isinstance(decision, PolicyDecision) or decision.allowed is not True:
            decision_id = decision.decision_id if isinstance(decision, PolicyDecision) and isinstance(decision.decision_id, str) and _IDENTIFIER.fullmatch(decision.decision_id) else None
            return self._denied(adapter_id, invocation.capability, "policy_denied",
                                decision_id)
        if not isinstance(decision.decision_id, str) or not _IDENTIFIER.fullmatch(decision.decision_id):
            return self._denied(adapter_id, invocation.capability, "invalid_policy_decision")
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
        stack = [(value, False, 0)]
        visited_items = 0
        pending_items = 1
        while stack:
            item, exiting, depth = stack.pop()
            if not exiting:
                pending_items -= 1
                visited_items += 1
            if isinstance(item, (dict, list)):
                marker = id(item)
                if exiting:
                    active.remove(marker)
                    continue
                if marker in active:
                    raise ValueError("cyclic payload is not JSON-compatible")
                if depth >= self._max_payload_depth:
                    raise ValueError("payload exceeds maximum nesting depth")
                active.add(marker)
                if isinstance(item, dict):
                    if any(not isinstance(key, str) for key in item):
                        raise TypeError("JSON object keys must be strings")
                    children = item.values()
                else:
                    children = item
                if visited_items + pending_items + len(item) > self._max_payload_items:
                    raise ValueError("payload exceeds configured item limit")
                pending_items += len(item)
                stack.append((item, True, depth))
                stack.extend((child, False, depth + 1) for child in children)
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
