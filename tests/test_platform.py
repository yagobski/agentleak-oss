"""Platform API: projects, runs, compare, stats (skipped without [gui])."""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from agentleak.core.store import Store  # noqa: E402
from agentleak.web import create_app  # noqa: E402


@pytest.fixture()
def client(tmp_path) -> TestClient:
    return TestClient(create_app(store=Store(str(tmp_path / "api.db"))))


def test_meta_lists_agent_types(client: TestClient):
    types = client.get("/api/meta").json()["agent_types"]
    assert any(a["id"] == "generic" for a in types)
    assert any(a["id"] == "langchain" for a in types)


def test_connect_snippet(client: TestClient):
    pid = client.post("/api/projects", json={"name": "P", "agent_type": "langchain"}).json()["id"]
    body = client.get(f"/api/projects/{pid}/connect").json()
    assert "AgentLeakClient" in body["snippet"]
    assert "LangChainCallback" in body["snippet"]
    assert body["framework"] == "LangChain"


def test_project_crud_via_api(client: TestClient):
    created = client.post("/api/projects", json={"name": "Support Bot", "agent_type": "crewai"}).json()
    pid = created["id"]
    assert created["agent_type"] == "crewai"

    assert any(p["id"] == pid for p in client.get("/api/projects").json())
    assert client.get(f"/api/projects/{pid}").json()["name"] == "Support Bot"

    patched = client.patch(f"/api/projects/{pid}", json={"description": "updated"}).json()
    assert patched["description"] == "updated"

    assert client.delete(f"/api/projects/{pid}").json()["deleted"] is True
    assert client.get(f"/api/projects/{pid}").status_code == 404


def test_create_project_requires_name(client: TestClient):
    assert client.post("/api/projects", json={"name": "  "}).status_code == 400


def test_run_creation_and_retrieval(client: TestClient):
    pid = client.post("/api/projects", json={"name": "P"}).json()["id"]
    run = client.post(f"/api/projects/{pid}/runs", json={"scenario_id": "healthcare_patient_summary"}).json()
    assert run["id"].startswith("run_")
    assert run["report"]["scoring"] == "agentrisk"
    assert run["verdict"] in {"High risk", "Fail"}

    runs = client.get(f"/api/projects/{pid}/runs").json()
    assert len(runs) == 1
    full = client.get(f"/api/runs/{run['id']}").json()
    assert full["report"]["risk_index"] == run["report"]["risk_index"]


def test_project_config_applies_to_runs(client: TestClient):
    # A project with only PII enabled should not report finance findings.
    pid = client.post("/api/projects", json={
        "name": "PiiOnly",
        "detectors": {"pii": True, "secrets": False, "healthcare": False, "finance": False, "hr": False},
    }).json()["id"]
    run = client.post(f"/api/projects/{pid}/runs", json={"scenario_id": "finance_loan_review"}).json()
    detectors = {f["detector"] for f in run["report"]["findings"]}
    assert detectors <= {"pii_detector"}


def test_compare_dominance(client: TestClient):
    pid = client.post("/api/projects", json={"name": "P"}).json()["id"]
    a = client.post(f"/api/projects/{pid}/runs", json={"scenario_id": "healthcare_patient_summary"}).json()
    b = client.post(f"/api/projects/{pid}/runs", json={"scenario_id": "customer_support_crm"}).json()
    res = client.post("/api/compare", json={"a": a["id"], "b": b["id"]}).json()
    assert res["dominance"] in {"a", "b", "neither"}


def test_stats_endpoint(client: TestClient):
    pid = client.post("/api/projects", json={"name": "P"}).json()["id"]
    client.post(f"/api/projects/{pid}/runs", json={"scenario_id": "hr_employee_case"})
    s = client.get("/api/stats").json()
    assert s["projects"] == 1 and s["runs"] == 1


def test_run_unknown_project_404(client: TestClient):
    assert client.post("/api/projects/nope/runs", json={"scenario_id": "hr_employee_case"}).status_code == 404
