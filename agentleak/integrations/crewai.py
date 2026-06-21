"""CrewAI integration.

CrewAI exposes ``step_callback`` and ``task_callback`` hooks. This adapter maps
agent steps to inter-agent messages and task outputs to final output.

Usage::

    from agentleak.integrations.crewai import CrewAICallback

    cb = CrewAICallback(run_id="run_001")
    crew = Crew(agents=[...], tasks=[...], step_callback=cb.step_callback,
                task_callback=cb.task_callback)
    crew.kickoff()
    result = cb.analyze()
"""

from __future__ import annotations

from typing import Any

from ..core.config import Config
from ..core.report import AnalysisResult
from ..core.runner import AgentLeakRunner
from .generic import TraceRecorder


class CrewAICallback(TraceRecorder):
    def __init__(self, run_id: str = "run", agent_name: str = "crewai_agent",
                 config: Config | None = None) -> None:
        super().__init__(run_id=run_id, agent_name=agent_name)
        self.config = config

    def step_callback(self, step: Any) -> None:
        """Receives an AgentStep / tool usage. Recorded as inter-agent + tool."""
        tool = getattr(step, "tool", None)
        tool_input = getattr(step, "tool_input", None)
        text = getattr(step, "text", None) or getattr(step, "log", None) or str(step)
        if tool is not None:
            self.tool_call(
                {"tool": tool, "tool_input": tool_input}, source="agent",
                target=str(tool), metadata={"tool_name": str(tool)},
            )
        self.inter_agent_message(text, source="agent", target="crew")

    def task_callback(self, task_output: Any) -> None:
        """Receives a TaskOutput; the raw result is the final output."""
        raw = getattr(task_output, "raw", None) or getattr(task_output, "result", None) or str(task_output)
        agent = getattr(task_output, "agent", "agent")
        self.final_output(raw, source=str(agent), target="user")

    def analyze(self) -> AnalysisResult:
        return AgentLeakRunner(self.config).analyze(self.trace)


__all__ = ["CrewAICallback"]
