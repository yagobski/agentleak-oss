"""Trace model and content-flattening tests."""

from __future__ import annotations

from agentleak.core.trace import CHANNELS, Channel, Event, Trace, content_to_text


def test_channels_list_matches_enum():
    assert set(CHANNELS) == {c.value for c in Channel}
    assert "tool_call" in CHANNELS


def test_add_event_assigns_sequential_ids():
    t = Trace(run_id="r")
    e1 = t.add_event("tool_call", "a")
    e2 = t.add_event("final_output", "b")
    assert e1.event_id == "evt_001"
    assert e2.event_id == "evt_002"
    assert len(t.events) == 2


def test_from_dict_fills_missing_ids():
    t = Trace.from_dict({
        "run_id": "r",
        "events": [
            {"channel": "tool_call", "content": "x"},
            {"channel": "log", "content": "y"},
        ],
    })
    assert [e.event_id for e in t.events] == ["evt_001", "evt_002"]


def test_content_to_text_flattens_dict_keys():
    text = content_to_text({"credit_score": 712, "account_number": "99887766"})
    assert "credit score: 712" in text
    assert "account number: 99887766" in text


def test_content_to_text_handles_nested_and_lists():
    text = content_to_text({"students": [{"student_name": "Emma"}, {"student_name": "Liam"}]})
    assert "student name: Emma" in text
    assert "student name: Liam" in text


def test_content_to_text_passthrough_string():
    assert content_to_text("hello world") == "hello world"


def test_event_searchable_text_uses_flattening():
    e = Event(channel=Channel.TOOL_CALL, content={"salary": 95000})
    assert "salary: 95000" in e.searchable_text


def test_events_for_channel_filters():
    t = Trace(run_id="r")
    t.add_event("tool_call", "a")
    t.add_event("log", "b")
    t.add_event("tool_call", "c")
    assert len(t.events_for_channel("tool_call")) == 2
    assert len(t.events_for_channel(Channel.LOG)) == 1


def test_round_trip_to_dict():
    t = Trace(run_id="r", agent_name="agent")
    t.add_event("tool_call", {"k": "v"})
    data = t.to_dict()
    again = Trace.from_dict(data)
    assert again.run_id == "r"
    assert again.events[0].channel_value == "tool_call"
