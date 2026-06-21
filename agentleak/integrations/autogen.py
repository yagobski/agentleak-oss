"""AutoGen integration.

AutoGen drives multi-agent conversations as lists of messages. This adapter
ingests a conversation (e.g. ``ChatResult.chat_history`` or any list of
``{"name"/"role", "content"}`` dicts) and maps it to inter-agent messages, with
the final assistant turn as the final output.

Usage::

    from agentleak.integrations.autogen import trace_from_messages
    from agentleak import AgentLeakRunner

    trace = trace_from_messages(chat_result.chat_history, run_id="run_001")
    result = AgentLeakRunner().analyze(trace)
"""

from __future__ import annotations

from typing import Any

from ..core.trace import Trace


def trace_from_messages(
    messages: list[dict[str, Any]] | list[Any],
    *,
    run_id: str = "run",
    agent_name: str = "autogen_agent",
) -> Trace:
    trace = Trace(run_id=run_id, agent_name=agent_name)
    msgs = list(messages)
    for i, msg in enumerate(msgs):
        if isinstance(msg, dict):
            name = msg.get("name") or msg.get("role") or "agent"
            content = msg.get("content", "")
            tool_calls = msg.get("tool_calls")
        else:  # object with attributes
            name = getattr(msg, "name", None) or getattr(msg, "role", "agent")
            content = getattr(msg, "content", "")
            tool_calls = getattr(msg, "tool_calls", None)

        if tool_calls:
            trace.add_event(
                channel="tool_call", content=tool_calls, source=str(name),
                target="tool", metadata={"origin": "autogen"},
            )

        is_last = i == len(msgs) - 1
        trace.add_event(
            channel="final_output" if is_last else "inter_agent_message",
            content=content or "",
            source=str(name),
            target="user" if is_last else "agent",
        )
    return trace


__all__ = ["trace_from_messages"]
