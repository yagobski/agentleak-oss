"""Detection primitives: severities, raw matches, findings, and the base
:class:`Detector` contract.

Detectors are deliberately simple and explainable (regex + dictionaries, no
LLM dependency). Each returns :class:`RawMatch` objects over a piece of text;
the runner enriches those into :class:`Finding` objects with event context,
ids, and redaction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @property
    def weight(self) -> int:
        """Numeric weight used by the scoring engine (spec section 9.1)."""
        return _SEVERITY_WEIGHTS[self]

    @property
    def rank(self) -> int:
        """Ordering rank (critical highest) for comparing severities."""
        return _SEVERITY_RANK[self]


_SEVERITY_WEIGHTS: dict[Severity, int] = {
    Severity.LOW: 1,
    Severity.MEDIUM: 3,
    Severity.HIGH: 7,
    Severity.CRITICAL: 10,
}

_SEVERITY_RANK: dict[Severity, int] = {
    Severity.LOW: 0,
    Severity.MEDIUM: 1,
    Severity.HIGH: 2,
    Severity.CRITICAL: 3,
}


def coerce_severity(value: str | Severity) -> Severity:
    if isinstance(value, Severity):
        return value
    return Severity(str(value).lower())


def redact(value: str, *, keep: int = 2) -> str:
    """Mask a sensitive value, keeping the first/last ``keep`` characters.

    ``TREM12345678`` -> ``TR********78``. Short values are fully masked so we
    never reveal more than a couple of characters.
    """
    text = str(value)
    if len(text) <= keep * 2:
        return "*" * len(text)
    middle = len(text) - keep * 2
    return f"{text[:keep]}{'*' * middle}{text[-keep:]}"


@dataclass
class RawMatch:
    """What a detector emits for a single hit, before event enrichment."""

    data_type: str
    severity: Severity
    confidence: float
    matched_value: str
    recommendation: str = ""
    detector: str = ""

    def __post_init__(self) -> None:
        self.severity = coerce_severity(self.severity)
        # Keep confidence in a sane [0, 1] band.
        self.confidence = max(0.0, min(1.0, float(self.confidence)))


@dataclass
class Finding:
    """A leak finding with full context, ready for scoring and reporting."""

    finding_id: str
    run_id: str
    event_id: str
    channel: str
    data_type: str
    severity: Severity
    confidence: float
    matched_value: str
    redacted_value: str
    detector: str
    recommendation: str = ""
    source: str = ""
    target: str = ""
    # AgentRisk severity level 1..4 (GDPR/Law-25 taxonomy). Filled by the runner.
    level: int = 2
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self, *, redact_values: bool = True) -> dict[str, Any]:
        """Serialize for reports.

        When ``redact_values`` is true (the privacy-preserving default), the
        raw matched value is omitted entirely and only the masked form is kept.
        """
        data: dict[str, Any] = {
            "finding_id": self.finding_id,
            "run_id": self.run_id,
            "event_id": self.event_id,
            "channel": self.channel,
            "data_type": self.data_type,
            "severity": self.severity.value,
            "level": self.level,
            "confidence": round(self.confidence, 3),
            "redacted_value": self.redacted_value,
            "detector": self.detector,
            "recommendation": self.recommendation,
            "source": self.source,
            "target": self.target,
        }
        if not redact_values:
            data["matched_value"] = self.matched_value
        return data


class Detector:
    """Base class for all detectors.

    Subclasses set :attr:`name` and implement :meth:`detect`, returning a list
    of :class:`RawMatch`. They must be pure and side-effect free.
    """

    name: str = "detector"

    def detect(self, text: str) -> list[RawMatch]:  # pragma: no cover - abstract
        raise NotImplementedError

    # Convenience for subclasses to stamp their own name on matches.
    def _match(
        self,
        *,
        data_type: str,
        severity: str | Severity,
        confidence: float,
        matched_value: str,
        recommendation: str = "",
    ) -> RawMatch:
        return RawMatch(
            data_type=data_type,
            severity=coerce_severity(severity),
            confidence=confidence,
            matched_value=matched_value,
            recommendation=recommendation,
            detector=self.name,
        )
