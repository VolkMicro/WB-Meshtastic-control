from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class IncomingEnvelope:
    kind: str
    node: str
    payload: dict[str, Any]
    raw_text: str
    source: str


@dataclass
class ActionSpec:
    type: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class RuleSpec:
    rule_id: str
    enabled: bool
    match: dict[str, Any]
    actions: list[ActionSpec]
