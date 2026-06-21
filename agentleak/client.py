"""Thin HTTP client to connect an agent to a running AgentLeak platform.

Lets your agent push traces to ``agentleak serve`` so runs show up in the web
UI under a project. Uses only the standard library (urllib) — no new deps.

Example::

    from agentleak import AgentLeakClient, capture, monitor

    @monitor(channel="tool_call")
    def call_crm(cid):
        return {"customer_email": "a@b.com", "account_id": "ACC-12345"}

    client = AgentLeakClient(project="support-bot")   # get-or-create by name
    with capture(run_id="run_001") as cap:
        call_crm(42)
    run = client.submit(cap.trace)        # appears in the platform
    print(run["risk_index"], run["verdict"])
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any


class AgentLeakError(RuntimeError):
    pass


class AgentLeakClient:
    def __init__(
        self,
        project: str | None = None,
        *,
        base_url: str = "http://127.0.0.1:8000",
        agent_type: str = "generic",
        timeout: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._agent_type = agent_type
        self._project_id: str | None = None
        if project is not None:
            self._project_id = self.ensure_project(project, agent_type=agent_type)["id"]

    # -- low level ------------------------------------------------------
    def _request(self, method: str, path: str, body: Any | None = None) -> Any:
        url = f"{self.base_url}{path}"
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode()
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")
            try:
                detail = json.loads(detail).get("detail", detail)
            except Exception:  # noqa: BLE001
                pass
            raise AgentLeakError(f"{exc.code} {detail}") from exc
        except urllib.error.URLError as exc:
            raise AgentLeakError(
                f"Could not reach AgentLeak at {self.base_url} — is `agentleak serve` running? ({exc.reason})"
            ) from exc

    # -- projects -------------------------------------------------------
    def list_projects(self) -> list[dict[str, Any]]:
        return self._request("GET", "/api/projects")

    def create_project(self, name: str, *, agent_type: str = "generic", **config: Any) -> dict[str, Any]:
        return self._request("POST", "/api/projects", {"name": name, "agent_type": agent_type, **config})

    def ensure_project(self, name: str, *, agent_type: str = "generic", **config: Any) -> dict[str, Any]:
        for p in self.list_projects():
            if p["name"] == name:
                return p
        return self.create_project(name, agent_type=agent_type, **config)

    # -- runs -----------------------------------------------------------
    def submit(self, trace: Any, *, project: str | None = None, source: str = "sdk") -> dict[str, Any]:
        """Analyze a trace on the server and store it as a run. Returns the run
        (including the full report). ``trace`` may be a Trace, a dict, or JSON.
        """
        pid = self._resolve_project(project)
        payload = {"trace": self._trace_payload(trace), "source": source}
        return self._request("POST", f"/api/projects/{pid}/runs", payload)

    def submit_capture(self, capture: Any, *, project: str | None = None) -> dict[str, Any]:
        return self.submit(capture.trace, project=project, source="sdk")

    def runs(self, *, project: str | None = None) -> list[dict[str, Any]]:
        pid = self._resolve_project(project)
        return self._request("GET", f"/api/projects/{pid}/runs")

    # -- helpers --------------------------------------------------------
    def _resolve_project(self, project: str | None) -> str:
        if project is not None:
            # treat as id if it looks like one, else get-or-create by name
            if project.startswith("proj_"):
                return project
            return self.ensure_project(project, agent_type=self._agent_type)["id"]
        if self._project_id is None:
            raise AgentLeakError("No project set. Pass project=... or construct the client with one.")
        return self._project_id

    @staticmethod
    def _trace_payload(trace: Any) -> Any:
        if hasattr(trace, "to_dict"):
            return trace.to_dict()
        if isinstance(trace, str):
            return json.loads(trace)
        return trace


def connect(project: str, *, base_url: str = "http://127.0.0.1:8000", agent_type: str = "generic") -> AgentLeakClient:
    """Convenience: ``client = agentleak.connect("my-agent")``."""
    return AgentLeakClient(project, base_url=base_url, agent_type=agent_type)
