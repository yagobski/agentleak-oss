"""Trace data model — the central format of AgentLeak OSS.

Everything (framework traces, JSON files, SDK calls) is normalized into a
:class:`Trace` made of :class:`Event` objects. The detection engine consumes
these and never touches framework-specific structures.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Channel(str, Enum):
    """Normalized leakage channels.

    A *channel* is *where* data appears in an agentic system. The product
    thesis is that the dangerous channels are the internal ones (tool calls,
    shared memory, logs) that output-only audits never inspect.
    """

    USER_INPUT = "user_input"
    FINAL_OUTPUT = "final_output"
    INTER_AGENT_MESSAGE = "inter_agent_message"
    SHARED_MEMORY = "shared_memory"
    TOOL_CALL = "tool_call"
    TOOL_RESPONSE = "tool_response"
    LOG = "log"
    GENERATED_FILE = "generated_file"


# Public list of supported channels (spec section 7.2).
CHANNELS: list[str] = [c.value for c in Channel]

# Content can be free text or a structured payload (e.g. tool arguments).
Content = str | dict[str, Any] | list[Any]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _humanize_key(key: str) -> str:
    return str(key).replace("_", " ").replace("-", " ").strip()


def content_to_text(content: Content) -> str:
    """Flatten any event content into a single searchable string.

    Detectors operate on text. Structured payloads (e.g. tool arguments) are
    flattened into readable ``key: value`` pairs — underscores/hyphens in keys
    become spaces — so that *both* pattern detectors (which see the raw values)
    and keyword-anchored detectors (which need ``credit score: 712`` rather than
    the JSON ``"credit_score":712``) work on structured content.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, dict):
        parts = [f"{_humanize_key(k)}: {content_to_text(v)}" for k, v in content.items()]
        return " | ".join(parts)
    if isinstance(content, (list, tuple)):
        return " | ".join(content_to_text(v) for v in content)
    return str(content)


class Event(BaseModel):
    """A single observable event in an agent execution."""

    model_config = ConfigDict(use_enum_values=True)

    event_id: str = Field(default="", description="Stable id; auto-filled if empty")
    channel: Channel
    source: str = Field(default="unknown", description="Who emitted the event")
    target: str = Field(default="unknown", description="Where it was headed")
    content: Content = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=_utcnow)

    @property
    def channel_value(self) -> str:
        """Channel as a plain string (works whether stored as enum or str)."""
        return self.channel.value if isinstance(self.channel, Channel) else str(self.channel)

    @property
    def searchable_text(self) -> str:
        """Text the detectors scan for this event."""
        return content_to_text(self.content)


class Trace(BaseModel):
    """A complete, normalized execution trace.

    This is the unit AgentLeak analyzes. Build one explicitly via the SDK
    (:meth:`add_event`), load one from JSON (:meth:`from_dict` /
    :meth:`from_json_file`), or produce one through an integration adapter.
    """

    model_config = ConfigDict(use_enum_values=True)

    run_id: str = Field(default="run", description="Unique id for this run")
    agent_name: str = Field(default="unknown_agent")
    scenario_id: str | None = None
    timestamp: datetime = Field(default_factory=_utcnow)
    events: list[Event] = Field(default_factory=list)

    def add_event(
        self,
        channel: str | Channel,
        content: Content = "",
        *,
        source: str = "unknown",
        target: str = "unknown",
        event_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Event:
        """Append an event and return it. Primary SDK entry point."""
        eid = event_id or f"evt_{len(self.events) + 1:03d}"
        event = Event(
            event_id=eid,
            channel=Channel(channel) if not isinstance(channel, Channel) else channel,
            source=source,
            target=target,
            content=content,
            metadata=metadata or {},
        )
        self.events.append(event)
        return event

    def events_for_channel(self, channel: str | Channel) -> list[Event]:
        value = channel.value if isinstance(channel, Channel) else str(channel)
        return [e for e in self.events if e.channel_value == value]

    # ------------------------------------------------------------------
    # Serialization helpers
    # ------------------------------------------------------------------
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Trace:
        """Build a trace from a plain dict, assigning event ids when missing."""
        events = data.get("events", [])
        normalized: list[dict[str, Any]] = []
        for i, raw in enumerate(events, start=1):
            event = dict(raw)
            if not event.get("event_id"):
                event["event_id"] = f"evt_{i:03d}"
            normalized.append(event)
        payload = {**data, "events": normalized}
        return cls.model_validate(payload)

    @classmethod
    def from_json_file(cls, path: str) -> Trace:
        with open(path, encoding="utf-8") as fh:
            return cls.from_dict(json.load(fh))

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
