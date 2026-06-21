"""LangGraph integration.

LangGraph is built on langchain-core, so the LangChain callback works directly
as a graph callback. We re-export it as ``AgentLeakCallback`` and add a helper
to ingest a final graph state (with a ``messages`` list) into a trace.

Usage::

    from agentleak.integrations.langgraph import AgentLeakCallback

    cb = AgentLeakCallback(run_id="run_001")
    graph.invoke(inputs, config={"callbacks": [cb]})
    result = cb.analyze()
"""

from __future__ import annotations

from typing import Any

from ..core.trace import Trace
from .langchain import LangChainCallback


class AgentLeakCallback(LangChainCallback):
    """LangGraph-flavored alias of the LangChain callback."""

    def __init__(self, run_id: str = "run", agent_name: str = "langgraph_agent",
                 **kw: Any) -> None:
        super().__init__(run_id=run_id, agent_name=agent_name, **kw)


def trace_from_state(
    state: dict[str, Any],
    *,
    run_id: str = "run",
    agent_name: str = "langgraph_agent",
) -> Trace:
    """Build a trace from a LangGraph state dict with a ``messages`` list.

    The last message is treated as the final output; earlier messages as
    inter-agent communication.
    """
    trace = Trace(run_id=run_id, agent_name=agent_name)
    messages = state.get("messages", []) or []
    for i, msg in enumerate(messages):
        content = getattr(msg, "content", None)
        if content is None and isinstance(msg, dict):
            content = msg.get("content", "")
        role = getattr(msg, "type", None) or (msg.get("role") if isinstance(msg, dict) else "agent")
        is_last = i == len(messages) - 1
        channel = "final_output" if is_last else "inter_agent_message"
        trace.add_event(channel=channel, content=content or "", source=str(role), target="user" if is_last else "agent")
    return trace


__all__ = ["AgentLeakCallback", "trace_from_state"]
