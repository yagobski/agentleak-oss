"""Generic integration: build a :class:`Trace` from arbitrary event dicts, or
record events incrementally from any framework's callbacks.

This is the foundation every framework adapter builds on. It has no third-party
dependencies and is the recommended path when no first-class adapter exists.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from ..core.trace import Channel, Trace


class TraceRecorder:
    """Accumulates events into a :class:`Trace`.

    Framework adapters subclass this and translate their native callbacks into
    :meth:`record` calls with the appropriate channel.
    """

    def __init__(self, run_id: str = "run", agent_name: str = "agent") -> None:
        self.trace = Trace(run_id=run_id, agent_name=agent_name)

    def record(
        self,
        channel: str | Channel,
        content: Any,
        *,
        source: str = "unknown",
        target: str = "unknown",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.trace.add_event(
            channel=channel, content=content, source=source, target=target,
            metadata=metadata or {},
        )

    # Convenience shortcuts for the common channels.
    def user_input(self, content: Any, **kw: Any) -> None:
        self.record(Channel.USER_INPUT, content, **kw)

    def tool_call(self, content: Any, **kw: Any) -> None:
        self.record(Channel.TOOL_CALL, content, **kw)

    def tool_response(self, content: Any, **kw: Any) -> None:
        self.record(Channel.TOOL_RESPONSE, content, **kw)

    def inter_agent_message(self, content: Any, **kw: Any) -> None:
        self.record(Channel.INTER_AGENT_MESSAGE, content, **kw)

    def shared_memory(self, content: Any, **kw: Any) -> None:
        self.record(Channel.SHARED_MEMORY, content, **kw)

    def log(self, content: Any, **kw: Any) -> None:
        self.record(Channel.LOG, content, **kw)

    def final_output(self, content: Any, **kw: Any) -> None:
        self.record(Channel.FINAL_OUTPUT, content, **kw)


def from_events(
    events: Iterable[dict[str, Any]],
    *,
    run_id: str = "run",
    agent_name: str = "agent",
    scenario_id: str | None = None,
) -> Trace:
    """Build a trace from a list of plain event dicts."""
    return Trace.from_dict({
        "run_id": run_id,
        "agent_name": agent_name,
        "scenario_id": scenario_id,
        "events": list(events),
    })


# The generic recorder is also the default "callback" surface.
AgentLeakCallback = TraceRecorder

__all__ = ["TraceRecorder", "AgentLeakCallback", "from_events"]
