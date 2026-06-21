"""Leak provenance + agent topology (core/flow.py)."""

from __future__ import annotations

from agentleak import AgentLeakRunner
from agentleak.core.flow import build_leak_paths, build_topology
from agentleak.core.trace import Trace


def _multi_agent_trace() -> Trace:
    t = Trace(run_id="ma", agent_name="multi")
    t.add_event("user_input", "Summarize the dispute", source="user", target="A1")
    t.add_event("tool_response", {"name": "Jane Doe", "ssn": "123-45-6789", "email": "jane@example.com"},
                source="datastore", target="A1")
    t.add_event("shared_memory", "memo Jane Doe ssn 123-45-6789", source="A1", target="memory")
    t.add_event("inter_agent_message", "review ssn 123-45-6789 for jane@example.com", source="A1", target="A2")
    t.add_event("tool_call", {"tool": "notify", "ssn": "123-45-6789"}, source="A2", target="external_api")
    t.add_event("final_output", "Handled internally.", source="A2", target="user")
    return t


def _report():
    return AgentLeakRunner().analyze(_multi_agent_trace())


def test_topology_classifies_nodes_into_lanes():
    r = _report()
    flow = build_topology(r.events, r.findings)
    kinds = {n["id"]: (n["kind"], n["lane"]) for n in flow["nodes"]}
    assert kinds["user"][0] == "user" and kinds["user"][1] == 0
    assert kinds["datastore"] == ("tool", 0)
    assert kinds["A1"] == ("agent", 1) and kinds["A2"] == ("agent", 1)
    assert kinds["memory"][1] == 2          # sink lane
    assert kinds["external_api"][1] == 2    # tool_call target is an exfil sink


def test_topology_flags_leak_edges_with_severity():
    r = _report()
    flow = build_topology(r.events, r.findings)
    leak_edges = {(e["source"], e["target"], e["channel"]): e for e in flow["edges"] if e["leaked"]}
    assert ("A1", "memory", "shared_memory") in leak_edges
    assert ("A1", "A2", "inter_agent_message") in leak_edges
    assert ("A2", "external_api", "tool_call") in leak_edges
    # SSN is L4
    assert leak_edges[("A1", "memory", "shared_memory")]["level"] == 4
    # the user_input / tool_response edges are sources, not leaks
    clean = {(e["source"], e["target"]) for e in flow["edges"] if not e["leaked"]}
    assert ("datastore", "A1") in clean


def test_leak_path_traces_origin_to_disclosure():
    r = _report()
    paths = build_leak_paths(r.events, r.findings, redact=True)
    ssn = next(p for p in paths if p["data_type"] == "ssn")
    # entered via tool_response (a source channel)
    assert ssn["entered_via"] == "tool_response"
    assert ssn["origin"]["kind"] == "source"
    # propagated across both agents and three disclosure channels
    assert set(ssn["channels"]) == {"shared_memory", "inter_agent_message", "tool_call"}
    assert set(ssn["agents"]) == {"A1", "A2"}
    assert ssn["leak_count"] == 3
    assert ssn["level_label"] == "L4"
    # value is redacted, never raw
    assert "123-45-6789" not in ssn["value"]
    # steps are ordered: first step is the source
    assert ssn["steps"][0]["kind"] == "source"
    assert any(s["kind"] == "leak" for s in ssn["steps"])


def test_secret_that_never_leaks_is_excluded():
    # A secret only ever on a baseline (source) channel must not appear.
    t = Trace(run_id="r")
    t.add_event("tool_response", {"ssn": "123-45-6789"}, source="db", target="A1")
    t.add_event("final_output", "Summary without identifiers.", source="A1", target="user")
    r = AgentLeakRunner().analyze(t)
    paths = build_leak_paths(r.events, r.findings)
    assert all(p["data_type"] != "ssn" for p in paths)


def test_flow_embedded_in_report_dict():
    d = _report().to_dict()
    assert "flow" in d and d["flow"]["nodes"]
    assert "leak_paths" in d and d["leak_paths"]
    assert d["leak_paths"][0]["level"] >= d["leak_paths"][-1]["level"]  # sorted desc


def test_empty_trace_has_empty_flow():
    d = AgentLeakRunner().analyze(Trace(run_id="empty")).to_dict()
    assert d["flow"]["nodes"] == []
    assert d["leak_paths"] == []


def test_markdown_export_includes_leak_paths():
    from agentleak.reporters import render

    md = render(_report().to_dict(), "markdown")
    assert "## Leak paths" in md
    assert "ssn" in md
    assert "tool_response" in md
    # raw secret never appears in the export
    assert "123-45-6789" not in md
