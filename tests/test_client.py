"""SDK client logic (HTTP layer mocked — no live server needed)."""

from __future__ import annotations

import pytest

from agentleak import Trace
from agentleak.client import AgentLeakClient, AgentLeakError


class FakeServer:
    def __init__(self) -> None:
        self.projects: list[dict] = []

    def request(self, method: str, path: str, body=None):
        if path == "/api/projects" and method == "GET":
            return list(self.projects)
        if path == "/api/projects" and method == "POST":
            p = {"id": f"proj_{len(self.projects)}", "name": body["name"], "agent_type": body.get("agent_type", "generic")}
            self.projects.append(p)
            return p
        if path.endswith("/runs") and method == "POST":
            return {"id": "run_1", "risk_index": 0.44, "verdict": "High risk", "report": body}
        raise AssertionError(f"unexpected {method} {path}")


@pytest.fixture()
def client(monkeypatch) -> AgentLeakClient:
    c = AgentLeakClient(base_url="http://test")  # project=None -> no network in __init__
    monkeypatch.setattr(c, "_request", FakeServer().request)
    return c


def test_ensure_project_get_or_create(client: AgentLeakClient):
    a = client.ensure_project("agent")
    b = client.ensure_project("agent")
    assert a["id"] == b["id"]  # second call reuses, doesn't duplicate
    assert client.create_project("other")["id"] != a["id"]


def test_submit_resolves_project_by_name(client: AgentLeakClient):
    trace = Trace(run_id="r")
    trace.add_event("tool_call", {"email": "a@b.com"})
    run = client.submit(trace, project="my-agent")
    assert run["verdict"] == "High risk"


def test_submit_without_project_raises(client: AgentLeakClient):
    with pytest.raises(AgentLeakError):
        client.submit(Trace(run_id="r"))


def test_trace_payload_accepts_trace_dict_and_json():
    assert AgentLeakClient._trace_payload(Trace(run_id="x"))["run_id"] == "x"
    assert AgentLeakClient._trace_payload({"a": 1}) == {"a": 1}
    assert AgentLeakClient._trace_payload('{"a": 1}') == {"a": 1}


def test_unreachable_server_raises_clean_error():
    c = AgentLeakClient(base_url="http://127.0.0.1:59999")  # nothing listening
    with pytest.raises(AgentLeakError):
        c.list_projects()


def test_init_with_project_creates_and_resolves(monkeypatch):
    server = FakeServer()
    monkeypatch.setattr(AgentLeakClient, "_request", lambda self, m, p, b=None: server.request(m, p, b))
    c = AgentLeakClient(project="bot", base_url="http://test")
    assert c._project_id is not None
    # submit with no explicit project uses the bound one
    run = c.submit(Trace(run_id="r"))
    assert run["id"] == "run_1"


def test_submit_capture_and_runs(client: AgentLeakClient, monkeypatch):
    client._project_id = "proj_0"
    monkeypatch.setattr(client, "_request", lambda m, p, b=None: [] if m == "GET" else {"id": "run_1"})

    class Cap:
        trace = Trace(run_id="r")

    assert client.submit_capture(Cap())["id"] == "run_1"
    assert client.runs() == []


def test_resolve_project_accepts_id(client: AgentLeakClient):
    assert client._resolve_project("proj_abc") == "proj_abc"  # id passthrough, no lookup


def test_request_http_error_parses_detail(monkeypatch):
    import io
    import urllib.error

    def boom(req, timeout=None):
        raise urllib.error.HTTPError(req.full_url, 404, "NF", {}, io.BytesIO(b'{"detail":"Project not found"}'))

    monkeypatch.setattr("agentleak.client.urllib.request.urlopen", boom)
    c = AgentLeakClient(base_url="http://test")
    with pytest.raises(AgentLeakError, match="Project not found"):
        c.list_projects()


def test_connect_helper(monkeypatch):
    monkeypatch.setattr(AgentLeakClient, "_request", lambda self, m, p, b=None: [{"id": "proj_0", "name": "x"}])
    from agentleak.client import connect

    c = connect("x", base_url="http://test")
    assert c._project_id == "proj_0"
