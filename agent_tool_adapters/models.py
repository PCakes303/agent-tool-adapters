"""Stable value objects for adapter invocation."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable, Mapping

@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    decision_id: str

@dataclass(frozen=True)
class Invocation:
    principal_id: str
    capability: str
    input_data: Any
    policy: Callable[["Invocation"], PolicyDecision]

@dataclass(frozen=True)
class InvocationResult:
    ok: bool
    adapter_id: str
    capability: str
    output: Any = None
    error_code: str | None = None
    error_message: str | None = None
    decision_id: str | None = None
