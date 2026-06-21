"""Normalize a scenario into a run context the agent runner can execute.

Works from an AgentLeak **spec** (objective + private_vault + tools) when one is
stored, and otherwise **derives** the context from the scenario's trace: the
task is the ``user_input`` and the private records are the ``tool_response``
payloads the original agent received. So every scenario — built-in trace,
uploaded trace, or imported spec — is runnable live.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RunContext:
    scenario_id: str
    request: str
    domain: str = "general"
    privacy_instruction: str = ""
    role: str = "assistant"
    records: list[dict[str, Any]] = field(default_factory=list)

    @property
    def has_data(self) -> bool:
        return any(self.records)


def _records_from_trace(trace: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for event in trace.get("events", []):
        if event.get("channel") == "tool_response":
            content = event.get("content")
            if isinstance(content, dict):
                out.append(content)
    return out


def _request_from_trace(trace: dict[str, Any], fallback: str) -> str:
    for event in trace.get("events", []):
        if event.get("channel") == "user_input":
            content = event.get("content")
            if isinstance(content, str) and content.strip():
                return content
    return fallback


def build_run_context(scenario: dict[str, Any]) -> RunContext:
    """Build a :class:`RunContext` from a scenario detail dict (spec and/or trace)."""
    sid = str(scenario.get("id") or scenario.get("scenario_id") or "scenario")
    spec = scenario.get("spec")
    if spec:
        objective = spec.get("objective", {}) or {}
        agents = spec.get("agents", []) or []
        records = [
            r.get("fields", {})
            for r in spec.get("private_vault", {}).get("records", []) or []
            if r.get("fields")
        ]
        return RunContext(
            scenario_id=sid,
            request=str(objective.get("user_request") or scenario.get("description") or "Complete the task."),
            domain=str(spec.get("vertical") or scenario.get("domain") or "general"),
            privacy_instruction=str(objective.get("privacy_instruction") or ""),
            role=str(agents[0].get("role", "assistant")) if agents else "assistant",
            records=records,
        )

    trace = scenario.get("trace") or {}
    return RunContext(
        scenario_id=sid,
        request=_request_from_trace(trace, str(scenario.get("description") or "Complete the task.")),
        domain=str(scenario.get("domain") or "general"),
        records=_records_from_trace(trace),
    )
