"""User-defined regex detectors loaded from ``agentleak.yaml``.

Each custom rule provides a name, a regex pattern, a severity, and a data type
so security teams can test for their own internal identifiers without touching
the codebase (spec section 8.6 / user story 3).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..core.detector import Detector, RawMatch, Severity, coerce_severity


@dataclass
class CustomRule:
    name: str
    pattern: str
    severity: Severity = Severity.MEDIUM
    data_type: str = "custom"
    confidence: float = 0.9
    recommendation: str = "Review this custom-flagged value before it leaves a trusted boundary."

    @classmethod
    def from_config(cls, raw: dict) -> CustomRule:
        return cls(
            name=str(raw["name"]),
            pattern=str(raw["pattern"]),
            severity=coerce_severity(raw.get("severity", "medium")),
            data_type=str(raw.get("data_type", raw.get("name", "custom"))),
            confidence=float(raw.get("confidence", 0.9)),
            recommendation=str(
                raw.get("recommendation", cls.recommendation)
            ),
        )


class CustomDetector(Detector):
    """Compiles a list of :class:`CustomRule` into a single detector."""

    name = "custom_detector"

    def __init__(self, rules: list[CustomRule] | None = None) -> None:
        self.rules: list[tuple[CustomRule, re.Pattern[str]]] = []
        for rule in rules or []:
            try:
                compiled = re.compile(rule.pattern)
            except re.error as exc:  # pragma: no cover - defensive
                raise ValueError(f"Invalid regex for custom detector '{rule.name}': {exc}") from exc
            self.rules.append((rule, compiled))

    @classmethod
    def from_config(cls, raw_rules: list[dict] | None) -> CustomDetector:
        return cls([CustomRule.from_config(r) for r in (raw_rules or [])])

    def detect(self, text: str) -> list[RawMatch]:
        matches: list[RawMatch] = []
        for rule, compiled in self.rules:
            for m in compiled.finditer(text):
                matches.append(RawMatch(
                    data_type=rule.data_type,
                    severity=rule.severity,
                    confidence=rule.confidence,
                    matched_value=m.group(0),
                    recommendation=rule.recommendation,
                    detector=f"custom:{rule.name}",
                ))
        return matches
