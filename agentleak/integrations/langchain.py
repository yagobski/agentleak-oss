"""LangChain integration.

``LangChainCallback`` is duck-typed: LangChain calls ``on_*`` methods on any
object passed via ``callbacks=[...]``, so this works without importing
LangChain. Tool inputs/outputs, LLM outputs, and agent actions are mapped onto
AgentLeak channels.

Usage::

    from agentleak.integrations.langchain import LangChainCallback

    cb = LangChainCallback(run_id="run_001")
    chain.invoke(inputs, config={"callbacks": [cb]})
    result = cb.analyze()
"""

from __future__ import annotations

from typing import Any

from ..core.config import Config
from ..core.report import AnalysisResult
from ..core.runner import AgentLeakRunner
from .generic import TraceRecorder


class LangChainCallback(TraceRecorder):
    def __init__(self, run_id: str = "run", agent_name: str = "langchain_agent",
                 config: Config | None = None) -> None:
        super().__init__(run_id=run_id, agent_name=agent_name)
        self.config = config

    # -- LangChain callback surface (duck-typed) ------------------------
    def on_tool_start(self, serialized: dict[str, Any], input_str: str, **kw: Any) -> None:
        name = (serialized or {}).get("name", "tool")
        self.tool_call(input_str, source="agent", target=name, metadata={"tool_name": name})

    def on_tool_end(self, output: Any, **kw: Any) -> None:
        self.tool_response(str(output), source="tool", target="agent")

    def on_agent_action(self, action: Any, **kw: Any) -> None:
        tool = getattr(action, "tool", "tool")
        tool_input = getattr(action, "tool_input", action)
        self.inter_agent_message(
            {"tool": tool, "tool_input": tool_input}, source="agent", target=tool,
        )

    def on_llm_end(self, response: Any, **kw: Any) -> None:
        text = _extract_llm_text(response)
        if text:
            self.final_output(text, source="llm", target="user")

    def on_text(self, text: str, **kw: Any) -> None:
        if text:
            self.log(text, source="chain", target="stdout")

    # -- analysis -------------------------------------------------------
    def analyze(self) -> AnalysisResult:
        return AgentLeakRunner(self.config).analyze(self.trace)


def _extract_llm_text(response: Any) -> str:
    # LangChain LLMResult has .generations: list[list[Generation]].
    generations = getattr(response, "generations", None)
    if generations:
        try:
            return generations[0][0].text  # type: ignore[index]
        except (IndexError, AttributeError):
            pass
    return str(response) if response is not None else ""


__all__ = ["LangChainCallback"]
