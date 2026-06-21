"""The orchestrator: run detectors over a trace, score the findings with
AgentRisk, and produce an :class:`AnalysisResult`.

This is the single seam everything else (CLI, SDK, integrations) goes through.
"""

from __future__ import annotations

from typing import Any

from ..detectors import build_detectors
from .agentrisk import DEFAULT_WEIGHTS, level_for
from .config import Config
from .detector import Detector, Finding, redact
from .report import AnalysisResult
from .scoring import score_findings
from .trace import Trace


class AgentLeakRunner:
    """Analyze traces for sensitive-data leakage, scored with AgentRisk.

    With no config, every built-in detector runs over every channel — handy for
    quick SDK use. Pass a :class:`Config` to honor ``agentleak.yaml`` toggles,
    channel filters, custom detectors, severity-level overrides, the audited
    vault scope, and scoring thresholds.
    """

    def __init__(self, config: Config | None = None) -> None:
        self.config = config
        if config is None:
            self.detectors: list[Detector] = build_detectors(None, None)
            self._channels: set[str] | None = None
            self._redact = True
            self._block_on_critical = True
            self._fail_below = 40
            self._project = "agentleak-project"
            self._weights: tuple[int, ...] = DEFAULT_WEIGHTS
            self._level_overrides: dict[str, int] = {}
            self._vault: Any = None
            self._scope_def: str | None = None
        else:
            self.detectors = build_detectors(
                config.detectors.as_dict(), config.custom_rules_raw()
            )
            self._channels = config.enabled_channels()
            self._redact = config.privacy.redact_values
            self._block_on_critical = config.scoring.block_on_critical
            self._fail_below = config.scoring.fail_below
            self._project = config.project.name
            self._weights = tuple(config.scoring.weights) or DEFAULT_WEIGHTS
            self._level_overrides = dict(config.scoring.level_overrides)
            self._vault, self._scope_def = config.vault_spec()

    def analyze(self, trace: Trace, *, vault: Any = None, scope_def: str | None = None) -> AnalysisResult:
        """Analyze a trace. An explicit ``vault`` (per-level counts, a list of
        secrets, or a raw ρ_S) overrides the config and the observed-reachable
        default for the AgentRisk denominator.
        """
        findings: list[Finding] = []
        counter = 0

        for event in trace.events:
            channel = event.channel_value
            if self._channels is not None and channel not in self._channels:
                continue

            text = event.searchable_text
            if not text:
                continue

            # Dedupe identical hits within one event (e.g. two detectors that
            # both match the same value).
            seen: set[tuple[str, str]] = set()
            for detector in self.detectors:
                for match in detector.detect(text):
                    key = (match.data_type, match.matched_value)
                    if key in seen:
                        continue
                    seen.add(key)
                    counter += 1
                    findings.append(Finding(
                        finding_id=f"finding_{counter:03d}",
                        run_id=trace.run_id,
                        event_id=event.event_id,
                        channel=channel,
                        data_type=match.data_type,
                        severity=match.severity,
                        confidence=match.confidence,
                        matched_value=match.matched_value,
                        redacted_value=redact(match.matched_value),
                        detector=match.detector or detector.name,
                        recommendation=match.recommendation,
                        source=event.source,
                        target=event.target,
                        level=level_for(match.data_type, match.severity, self._level_overrides),
                        metadata=dict(event.metadata),
                    ))

        # Stable, readable ordering: highest severity level first, then confidence.
        findings.sort(key=lambda f: (-f.level, -f.confidence))

        score = score_findings(
            findings,
            weights=self._weights,
            level_overrides=self._level_overrides,
            vault=vault if vault is not None else self._vault,
            scope_def=scope_def or self._scope_def,
        )

        return AnalysisResult(
            run_id=trace.run_id,
            agent_name=trace.agent_name,
            scenario_id=trace.scenario_id,
            score=score,
            findings=findings,
            project_name=self._project,
            redact_values=self._redact,
            block_on_critical=self._block_on_critical,
            fail_below=self._fail_below,
            event_count=len(trace.events),
        )


def analyze(trace: Trace, config: Config | None = None, **kwargs: Any) -> AnalysisResult:
    """Functional shortcut for ``AgentLeakRunner(config).analyze(trace)``."""
    return AgentLeakRunner(config).analyze(trace, **kwargs)
