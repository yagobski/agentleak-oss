"""AgentLeak OSS — open-source privacy-leakage testing for AI agents.

Quick start::

    from agentleak import Trace, AgentLeakRunner

    trace = Trace(run_id="demo")
    trace.add_event(
        channel="tool_call", source="agent", target="crm",
        content={"customer_email": "test@example.com", "account_id": "ACC-12345"},
    )
    trace.add_event(channel="final_output", content="All set!")

    result = AgentLeakRunner().analyze(trace)
    print(result.privacy_score, result.verdict)
"""

from __future__ import annotations

__version__ = "0.4.1"

from .client import AgentLeakClient, connect
from .core.agentrisk import AgentRiskReport, compute_agentrisk, dominates, level_for
from .core.config import Config
from .core.detector import Finding, RawMatch, Severity, redact
from .core.report import AnalysisResult
from .core.runner import AgentLeakRunner, analyze
from .core.scenario import Scenario
from .core.scoring import Score, score_findings, verdict_for
from .core.store import Store
from .core.trace import CHANNELS, Channel, Event, Trace
from .sdk import Capture, capture, monitor, record

__all__ = [
    "__version__",
    # core data model
    "Trace",
    "Event",
    "Channel",
    "CHANNELS",
    # detection / scoring
    "AgentLeakRunner",
    "analyze",
    "AnalysisResult",
    "Finding",
    "RawMatch",
    "Severity",
    "Score",
    "score_findings",
    "verdict_for",
    "redact",
    # agentrisk
    "AgentRiskReport",
    "compute_agentrisk",
    "dominates",
    "level_for",
    # config / scenarios
    "Config",
    "Scenario",
    # sdk
    "capture",
    "Capture",
    "monitor",
    "record",
    # platform
    "AgentLeakClient",
    "connect",
    "Store",
]
