"""SDK tests: capture context manager and the @monitor decorator."""

from __future__ import annotations

from agentleak import AgentLeakRunner, Trace, capture, monitor, record


def test_trace_builder_and_runner():
    trace = Trace(run_id="demo")
    trace.add_event(
        channel="tool_call", source="agent", target="crm",
        content={"customer_email": "test@example.com", "account_id": "ACC-12345"},
    )
    trace.add_event(channel="final_output", content="All set.")
    result = AgentLeakRunner().analyze(trace)
    types = {f.data_type for f in result.findings}
    assert "email" in types
    assert "client_identifier" in types


def test_monitor_records_only_inside_capture():
    @monitor(channel="tool_call")
    def call_crm(customer_id):
        return {"customer_email": "x@y.com"}

    # Outside a capture: no-op, returns normally.
    assert call_crm(1) == {"customer_email": "x@y.com"}

    with capture(run_id="run_001") as cap:
        call_crm(42)
    assert len(cap.trace.events) == 1
    event = cap.trace.events[0]
    assert event.channel_value == "tool_call"
    assert "x@y.com" in event.searchable_text

    result = cap.analyze()
    assert any(f.data_type == "email" for f in result.findings)


def test_record_helper_appends_to_active_capture():
    with capture(run_id="r") as cap:
        record("log", "user email leaked@example.com", source="svc")
    assert len(cap.trace.events) == 1
    assert cap.trace.events[0].channel_value == "log"


def test_capture_restores_previous_active():
    from agentleak.sdk import active_capture
    assert active_capture() is None
    with capture(run_id="outer"):
        assert active_capture().trace.run_id == "outer"
        with capture(run_id="inner"):
            assert active_capture().trace.run_id == "inner"
        assert active_capture().trace.run_id == "outer"
    assert active_capture() is None
