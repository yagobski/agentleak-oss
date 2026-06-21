"""Core engine: trace model, detectors contract, scoring, config, runner."""

from __future__ import annotations

from .agentrisk import (
    AgentRiskReport,
    compute_agentrisk,
    dominates,
    level_for,
)
from .config import Config
from .detector import Detector, Finding, RawMatch, Severity, redact
from .report import AnalysisResult
from .runner import AgentLeakRunner, analyze
from .scenario import Scenario
from .scoring import Score, score_findings, verdict_for
from .trace import CHANNELS, Channel, Event, Trace

__all__ = [
    "Config",
    "Detector",
    "Finding",
    "RawMatch",
    "Severity",
    "redact",
    "AnalysisResult",
    "AgentLeakRunner",
    "analyze",
    "Scenario",
    "Score",
    "score_findings",
    "verdict_for",
    "AgentRiskReport",
    "compute_agentrisk",
    "dominates",
    "level_for",
    "CHANNELS",
    "Channel",
    "Event",
    "Trace",
]
