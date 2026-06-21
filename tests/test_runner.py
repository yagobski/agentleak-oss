"""End-to-end runner tests — the product's core promise."""

from __future__ import annotations

from agentleak import AgentLeakRunner, Trace
from agentleak.core.config import Config
from agentleak.scenarios import load_example_trace


def test_healthcare_demo_leaks_internally_not_in_output():
    """The headline: clean final output, leaks in internal channels."""
    trace = load_example_trace("healthcare_patient_summary")
    result = AgentLeakRunner().analyze(trace)

    channels = {cr.channel for cr in result.score.channel_risks}
    # Final output and tool_response (a source) carry no agent leak.
    assert "final_output" not in channels
    assert "tool_response" not in channels
    # Internal disclosure channels do leak.
    assert "shared_memory" in channels
    # shared_memory carries a Level-4 leak (the NAM health identifier).
    mem = next(cr for cr in result.score.channel_risks if cr.channel == "shared_memory")
    assert mem.level == 4
    assert mem.ri > 0
    # Partial leakage -> a real but sub-maximal Risk Index.
    assert 0.3 < result.risk_index < 0.9
    assert result.verdict in {"High risk", "Fail"}
    assert result.has_critical is True   # NAM + diagnosis (L4) leaked to memory
    assert result.blocked is True


def test_tool_response_is_a_source_not_a_leak():
    # A secret returned by a tool but never re-emitted is in the vault, not leaked.
    from agentleak import Trace
    trace = Trace(run_id="r")
    trace.add_event("tool_call", {"query": "lookup"})
    trace.add_event("tool_response", {"ssn": "412-55-9087"})   # received, not leaked
    trace.add_event("final_output", "Done.")
    result = AgentLeakRunner().analyze(trace)
    assert result.risk_index == 0.0          # nothing emitted onto a disclosure channel
    assert {f.channel for f in result.findings} == {"tool_response"}


def test_runner_assigns_finding_ids_and_context():
    trace = Trace(run_id="run_x", agent_name="a")
    trace.add_event("tool_call", {"email": "a@b.com"}, source="agent", target="crm")
    result = AgentLeakRunner().analyze(trace)
    assert result.findings
    f = result.findings[0]
    assert f.finding_id.startswith("finding_")
    assert f.run_id == "run_x"
    assert f.channel == "tool_call"
    assert f.target == "crm"


def test_runner_dedupes_same_value_in_event():
    # Two detectors might match the same value; the runner keeps one.
    trace = Trace(run_id="r")
    trace.add_event("log", "email a@b.com a@b.com")  # same value twice
    result = AgentLeakRunner().analyze(trace)
    emails = [f for f in result.findings if f.data_type == "email"]
    assert len(emails) == 1


def test_channel_filter_from_config_excludes_disabled_channels():
    cfg = Config.from_dict({
        "channels": ["final_output"],  # only scan final output
        "detectors": {"pii": True, "secrets": True, "healthcare": True},
    })
    trace = Trace(run_id="r")
    trace.add_event("tool_call", {"email": "a@b.com"})  # should be ignored
    trace.add_event("final_output", "contact a@b.com")  # scanned
    result = AgentLeakRunner(cfg).analyze(trace)
    channels = {f.channel for f in result.findings}
    assert channels == {"final_output"}


def test_clean_trace_passes():
    trace = Trace(run_id="r")
    trace.add_event("final_output", "Your request has been processed successfully.")
    result = AgentLeakRunner().analyze(trace)
    assert result.findings == []
    assert result.privacy_score == 100
    assert result.verdict == "Pass"
    assert result.blocked is False


def test_redact_values_off_includes_raw():
    cfg = Config.from_dict({"privacy": {"redact_values": False},
                            "detectors": {"pii": True}})
    trace = Trace(run_id="r")
    trace.add_event("log", "email leaked@example.com")
    result = AgentLeakRunner(cfg).analyze(trace)
    data = result.to_dict()
    assert any("leaked@example.com" == f.get("matched_value") for f in data["findings"])
