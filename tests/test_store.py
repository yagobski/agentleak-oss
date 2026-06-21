"""SQLite store: projects + runs persistence."""

from __future__ import annotations

import pytest

from agentleak import AgentLeakRunner
from agentleak.core.store import Store
from agentleak.scenarios import load_example_trace


@pytest.fixture()
def store(tmp_path) -> Store:
    return Store(str(tmp_path / "test.db"))


def _report():
    return AgentLeakRunner().analyze(load_example_trace("healthcare_patient_summary")).to_dict()


def test_project_crud(store: Store):
    p = store.create_project("My Agent", agent_type="langchain", description="d", config={"redact": True})
    assert p["id"].startswith("proj_")
    assert p["agent_type"] == "langchain"
    assert store.get_project(p["id"])["name"] == "My Agent"
    assert len(store.list_projects()) == 1

    updated = store.update_project(p["id"], name="Renamed")
    assert updated["name"] == "Renamed"
    assert store.delete_project(p["id"]) is True
    assert store.get_project(p["id"]) is None


def test_invalid_agent_type_falls_back(store: Store):
    p = store.create_project("x", agent_type="bogus")
    assert p["agent_type"] == "generic"


def test_get_project_by_name(store: Store):
    store.create_project("dup")
    assert store.get_project_by_name("dup") is not None
    assert store.get_project_by_name("missing") is None


def test_run_lifecycle_and_aggregates(store: Store):
    p = store.create_project("agent")
    run = store.create_run(p["id"], _report(), source="sdk")
    assert run["id"].startswith("run_")
    assert run["verdict"] in {"High risk", "Fail"}
    assert "report" in run and run["report"]["scoring"] == "agentrisk"

    runs = store.list_runs(p["id"])
    assert len(runs) == 1
    assert "report" not in runs[0]  # list is summary-only

    # project aggregates update
    proj = store.get_project(p["id"])
    assert proj["run_count"] == 1
    assert proj["avg_risk_index"] is not None
    assert proj["last_run"]["id"] == run["id"]

    assert store.delete_run(run["id"]) is True
    assert store.get_run(run["id"]) is None


def test_delete_project_cascades_runs(store: Store):
    p = store.create_project("agent")
    store.create_run(p["id"], _report())
    store.delete_project(p["id"])
    assert store.list_runs(p["id"]) == []


def test_stats(store: Store):
    p = store.create_project("agent")
    store.create_run(p["id"], _report())
    s = store.stats()
    assert s["projects"] == 1
    assert s["runs"] == 1
    assert s["avg_risk_index"] is not None
    assert len(s["recent_runs"]) == 1


def _trace():
    return load_example_trace("healthcare_patient_summary").to_dict()


def test_scenario_crud(store: Store):
    sc = store.create_scenario(
        "My scenario", _trace(), domain="finance", description="d",
        sensitive_data=["ssn", "email"], tags=["t"], difficulty="hard",
    )
    assert sc["id"].startswith("sce_")
    assert sc["domain"] == "finance"
    assert sc["builtin"] is False
    assert "trace" in sc and sc["trace"]["events"]

    listed = store.list_scenarios()
    assert len(listed) == 1
    assert "trace" not in listed[0]  # list is summary-only

    assert store.get_scenario(sc["id"], with_trace=False).get("trace") is None
    assert store.delete_scenario(sc["id"]) is True
    assert store.get_scenario(sc["id"]) is None


def test_scenario_stores_and_returns_spec(store: Store):
    spec = {"scenario_id": "s1", "objective": {"user_request": "do it"}, "private_vault": {"records": []}}
    sc = store.create_scenario("S", _trace(), spec=spec)
    assert sc["has_spec"] is True
    assert store.get_scenario(sc["id"])["spec"] == spec
    # summaries advertise has_spec without carrying the body
    summary = store.list_scenarios()[0]
    assert summary["has_spec"] is True and "spec" not in summary


def test_scenario_without_spec_has_none(store: Store):
    sc = store.create_scenario("S", _trace())
    assert sc["has_spec"] is False
    assert store.get_scenario(sc["id"])["spec"] is None


def test_scenario_import_idempotency_helpers(store: Store):
    assert store.scenario_exists("pack_a", "origin_1") is False
    assert store.count_pack_scenarios("pack_a") == 0

    store.create_scenario("S", _trace(), source="imported", pack_id="pack_a", origin_id="origin_1")
    assert store.scenario_exists("pack_a", "origin_1") is True
    assert store.scenario_exists("pack_a", "origin_2") is False
    assert store.scenario_exists("pack_a", "") is False  # blank origin never matches
    assert store.count_pack_scenarios("pack_a") == 1
