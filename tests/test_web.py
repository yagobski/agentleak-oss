"""Web GUI tests (skipped if the [gui] extra isn't installed)."""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from agentleak.web import create_app  # noqa: E402


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(create_app())


def test_spa_served(client: TestClient):
    r = client.get("/")
    assert r.status_code == 200
    # The built React shell mounts on #root and links a hashed asset bundle.
    assert 'id="root"' in r.text
    assert "AgentLeak" in r.text


def test_meta_endpoint(client: TestClient):
    m = client.get("/api/meta").json()
    assert {"version", "channels", "detectors", "agent_types"} <= set(m)
    assert "tool_call" in m["channels"]
    assert "pii" in m["detectors"]
    assert any(a["id"] == "generic" for a in m["agent_types"])


def test_scenarios_endpoint(client: TestClient):
    ids = {s["id"] for s in client.get("/api/scenarios").json()}
    assert "healthcare_patient_summary" in ids


def test_example_endpoint(client: TestClient):
    assert client.get("/api/example/healthcare_patient_summary").json()["events"]


def test_example_unknown_404(client: TestClient):
    assert client.get("/api/example/nope").status_code == 404


def test_analyze_scenario(client: TestClient):
    d = client.post("/api/analyze", json={"scenario_id": "healthcare_patient_summary"}).json()
    assert d["scoring"] == "agentrisk"
    assert d["verdict"] in {"High risk", "Fail"}
    assert d["blocked"] is True


def test_analyze_with_explicit_vault(client: TestClient):
    ex = client.get("/api/example/finance_loan_review").json()
    d = client.post("/api/analyze", json={
        "trace": ex,
        "vault": {"mode": "explicit", "levels": {1: 5, 2: 3, 3: 2, 4: 1}},
    }).json()
    assert d["rho_s"] == 21


def test_analyze_detector_toggles(client: TestClient):
    ex = client.get("/api/example/finance_loan_review").json()
    d = client.post("/api/analyze", json={
        "trace": ex,
        "detectors": {"pii": True, "secrets": False, "healthcare": False, "finance": False, "hr": False},
    }).json()
    assert {f["detector"] for f in d["findings"]} <= {"pii_detector"}


def test_analyze_custom_detector(client: TestClient):
    d = client.post("/api/analyze", json={
        "trace": {"run_id": "r", "events": [{"channel": "tool_call", "content": "ref PROJECT-ABC-1234"}]},
        "detectors": {"pii": False, "secrets": False, "healthcare": False, "finance": False, "hr": False},
        "custom_detectors": [{"name": "proj", "pattern": r"PROJECT-[A-Z]{3}-[0-9]{4}", "severity": "high"}],
    }).json()
    assert any(f["detector"] == "custom:proj" for f in d["findings"])


def test_analyze_bad_trace_400(client: TestClient):
    assert client.post("/api/analyze", json={"trace": "not json"}).status_code == 400


@pytest.mark.parametrize("fmt", ["json", "html", "markdown"])
def test_report_formats(client: TestClient, fmt: str):
    r = client.post(f"/api/report/{fmt}", json={"scenario_id": "healthcare_patient_summary"})
    assert r.status_code == 200
    assert len(r.text) > 0


def test_report_bad_format_400(client: TestClient):
    assert client.post("/api/report/pdf", json={"scenario_id": "healthcare_patient_summary"}).status_code == 400
