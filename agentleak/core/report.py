"""The analysis result object — what :class:`AgentLeakRunner` returns and what
every reporter renders.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from . import compliance as _compliance
from . import flow as _flow
from .agentrisk import BASELINE_CHANNELS, LEVEL_LABELS
from .detector import Finding, Severity
from .scoring import Score, badge_for_level

# Standard, channel-level guidance surfaced when a given channel leaks
# (spec section 13.4). Keyed by channel.
STANDARD_RECOMMENDATIONS: dict[str, str] = {
    "tool_call": "Mask or strip sensitive fields before passing arguments to external tools.",
    "tool_response": "Filter tool responses; do not propagate raw sensitive fields downstream.",
    "shared_memory": "Disable persistent memory for sensitive workflows or store references, not raw values.",
    "log": "Stop logging full payloads; redact sensitive fields at the logging boundary.",
    "inter_agent_message": "Reduce the data shared between agents; separate permissions per agent role.",
    "generated_file": "Add a redaction filter before any document is published or exported.",
    "final_output": "Apply an output guardrail that strips identifiers from the final answer.",
}

GENERAL_RECOMMENDATIONS: list[str] = [
    "Add a human approval step before publishing documents that may contain personal data.",
    "Give each agent the least privilege it needs; don't broadcast sensitive context.",
]


@dataclass
class AnalysisResult:
    run_id: str
    agent_name: str
    scenario_id: str | None
    score: Score
    findings: list[Finding]
    project_name: str = "agentleak-project"
    redact_values: bool = True
    block_on_critical: bool = True
    fail_below: int = 40
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_count: int = 0
    # Lightweight event log ({event_id, channel, source, target}) for building
    # the leak-path and topology views. Filled by the runner.
    events: list[dict[str, Any]] = field(default_factory=list)

    # -- convenience accessors (used by the SDK and reporters) -----------
    @property
    def privacy_score(self) -> int:
        return self.score.privacy_score

    @property
    def risk_index(self) -> float:
        """The AgentRisk Risk Index RI in [0, 1]."""
        return self.score.risk_index

    @property
    def risk_score(self) -> float:
        # Backwards-friendly alias for the Risk Index.
        return self.score.risk_index

    @property
    def verdict(self) -> str:
        return self.score.verdict

    @property
    def has_critical(self) -> bool:
        return self.score.has_critical

    @property
    def blocked(self) -> bool:
        """True when this run should fail a CI gate."""
        return self.privacy_score < self.fail_below or (
            self.block_on_critical and self.has_critical
        )

    # -- findings views --------------------------------------------------
    def leaked_findings(self) -> list[Finding]:
        """Findings on disclosure channels — i.e. actual leaks (not sources)."""
        return [f for f in self.findings if f.channel not in BASELINE_CHANNELS]

    # -- recommendations -------------------------------------------------
    def recommendations(self) -> list[str]:
        recs: list[str] = []
        leaking_channels = {f.channel for f in self.leaked_findings()}
        # Channel guidance, ordered by the channel's risk contribution.
        for cr in self.score.channel_risks:
            advice = STANDARD_RECOMMENDATIONS.get(cr.channel)
            if advice and advice not in recs:
                recs.append(advice)
        if leaking_channels:
            for advice in GENERAL_RECOMMENDATIONS:
                if advice not in recs:
                    recs.append(advice)
        return recs

    # -- serialization ---------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        agentrisk = self.score.agentrisk.to_dict()
        level_profile = {LEVEL_LABELS[k]: self.score.level_profile.get(k, 0) for k in (1, 2, 3, 4)}
        leaked = self.leaked_findings()
        data: dict[str, Any] = {
            "report": "agentleak",
            "version": 2,
            "scoring": "agentrisk",
            "project": self.project_name,
            "run_id": self.run_id,
            "agent_name": self.agent_name,
            "scenario_id": self.scenario_id,
            "generated_at": self.generated_at.isoformat(),
            "event_count": self.event_count,
            "privacy_score": self.privacy_score,
            "verdict": self.verdict,
            "risk_index": self.risk_index,
            "wsl": self.score.wsl,
            "rho_s": self.score.rho_s,
            "scope_def": self.score.agentrisk.scope_def,
            "blocked": self.blocked,
            "summary": {
                "total_findings": len(leaked),
                "detected_total": len(self.findings),
                "leaked_secrets": self.score.agentrisk.leaked_count,
                "vault_secrets": self.score.agentrisk.vault_count,
                "level_profile": level_profile,
                "vault_level_profile": agentrisk["vault_level_profile"],
                "has_critical": self.has_critical,
            },
            "channel_risks": [
                {
                    "channel": cr.channel,
                    "level": cr.badge,           # color vocab: critical/high/medium/low
                    "level_label": cr.label,     # L1..L4
                    "ri": cr.ri,
                    "risk_contribution": cr.ri,  # bar magnitude
                    "finding_count": cr.finding_count,
                }
                for cr in self.score.channel_risks
            ],
            "findings": [self._finding_dict(f) for f in leaked],
            "recommendations": self.recommendations(),
            "agentrisk": agentrisk,
        }
        data["compliance"] = _compliance.evaluate(data)
        data["flow"] = _flow.build_topology(self.events, self.findings)
        data["leak_paths"] = _flow.build_leak_paths(
            self.events, self.findings, redact=self.redact_values
        )
        return data

    def _finding_dict(self, f: Finding) -> dict[str, Any]:
        data = f.to_dict(redact_values=self.redact_values)
        data["level_label"] = LEVEL_LABELS.get(f.level, "L?")
        data["badge"] = badge_for_level(f.level)
        return data

    @staticmethod
    def severity_order() -> list[str]:
        return [s.value for s in (Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW)]
