"""Scenario model.

A scenario is a named, domain-specific privacy test: a description, the kinds
of sensitive data it involves, the behavior a well-behaved agent should
exhibit, and a bundled synthetic trace that demonstrates the failure mode.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Scenario:
    id: str
    domain: str
    description: str
    sensitive_data: list[str] = field(default_factory=list)
    expected_behavior: list[str] = field(default_factory=list)
    # Filename (under the packaged ``examples/`` directory) of a trace that
    # demonstrates this scenario.
    example_trace: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "domain": self.domain,
            "description": self.description,
            "sensitive_data": list(self.sensitive_data),
            "expected_behavior": list(self.expected_behavior),
            "example_trace": self.example_trace,
        }
