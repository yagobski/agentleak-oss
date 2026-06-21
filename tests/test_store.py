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
