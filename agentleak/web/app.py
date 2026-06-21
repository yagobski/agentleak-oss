"""FastAPI app for the local AgentLeak platform.

Everything runs locally — traces are analyzed in-process and stored in a local
SQLite database; nothing leaves the machine. The frontend is a React + shadcn/ui
single-page app built into ``agentleak/web/static`` (source in
``agentleak/web/frontend``).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .. import __version__
from ..core.agentrisk import dominates
from ..core.config import Config
from ..core.report import AnalysisResult
from ..core.runner import AgentLeakRunner
from ..core.store import Store
from ..core.trace import CHANNELS, Trace
from ..detectors import BUILTIN_DETECTORS
from ..integrations import registry
from ..reporters import render
from ..scenarios import list_scenarios, load_example_trace

_STATIC_DIR = Path(__file__).resolve().parent / "static"
_GUI_IMPORT_ERROR = (
    "The web GUI needs FastAPI and uvicorn. Install them with:\n"
    "    pip install 'agentleak[gui]'"
)


# ----------------------------------------------------------------------
# config helpers
# ----------------------------------------------------------------------
def _config_data(settings: dict[str, Any]) -> dict[str, Any]:
    """Translate UI/project settings into agentleak.yaml config data."""
    data: dict[str, Any] = {}
    detectors = settings.get("detectors")
    if isinstance(detectors, dict):
        data["detectors"] = {k: bool(v) for k, v in detectors.items()}
    rules = settings.get("custom_detectors")
    if isinstance(rules, list) and rules:
        data["custom_detectors"] = [
            {
                "name": str(r["name"]),
                "pattern": str(r["pattern"]),
                "severity": str(r.get("severity", "high")),
                "data_type": str(r.get("data_type", r.get("name", "custom"))),
            }
            for r in rules
            if r.get("name") and r.get("pattern")
        ]
    if "redact" in settings:
        data["privacy"] = {"redact_values": bool(settings["redact"])}
    vault = settings.get("vault") or {}
    if vault.get("mode") == "explicit" and vault.get("levels"):
        levels = {int(k): int(v) for k, v in vault["levels"].items() if int(v) > 0}
        if levels:
            data["vault"] = {"levels": levels}
    return data


def _trace_from_payload(payload: dict[str, Any]) -> Trace:
    if payload.get("scenario_id"):
        return load_example_trace(payload["scenario_id"])
    trace = payload.get("trace")
    if not trace:
        raise ValueError("Provide a 'trace' object or a 'scenario_id'.")
    if isinstance(trace, str):
        trace = json.loads(trace)
    return Trace.from_dict(trace)


def _analyze(payload: dict[str, Any], *, project_name: str | None = None) -> AnalysisResult:
    data = _config_data(payload)
    if project_name:
        data["project"] = {"name": project_name}
    cfg = Config.from_dict(data) if data else None
    trace = _trace_from_payload(payload)
    return AgentLeakRunner(cfg).analyze(trace)


def _level_profile_ints(report: dict[str, Any]) -> dict[int, int]:
    lp = report.get("summary", {}).get("level_profile", {})
    return {n: int(lp.get(f"L{n}", 0)) for n in (1, 2, 3, 4)}


# ----------------------------------------------------------------------
def create_app(store: Store | None = None):  # noqa: ANN201
    try:
        from fastapi import Body, FastAPI, HTTPException
        from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse
        from fastapi.staticfiles import StaticFiles
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(_GUI_IMPORT_ERROR) from exc

    db = store or Store()
    app = FastAPI(title="AgentLeak", description="Local privacy-leakage platform (AgentRisk)")

    # -- meta / library ------------------------------------------------
    @app.get("/api/meta")
    def meta() -> dict[str, Any]:
        return {
            "version": __version__,
            "channels": list(CHANNELS),
            "detectors": list(BUILTIN_DETECTORS),
            "agent_types": registry.frameworks(),
        }

    @app.get("/api/scenarios")
    def scenarios() -> list[dict[str, Any]]:
        return [s.to_dict() for s in list_scenarios()]

    @app.get("/api/example/{scenario_id}")
    def example(scenario_id: str) -> dict[str, Any]:
        try:
            return load_example_trace(scenario_id).to_dict()
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/stats")
    def stats() -> dict[str, Any]:
        return db.stats()

    # -- stateless playground analysis ---------------------------------
    @app.post("/api/analyze")
    def analyze(payload: dict[str, Any] = Body(...)) -> JSONResponse:
        try:
            result = _analyze(payload)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return JSONResponse(result.to_dict())

    @app.post("/api/report/{fmt}")
    def report(fmt: str, payload: dict[str, Any] = Body(...)):
        if fmt not in {"json", "html", "markdown"}:
            raise HTTPException(status_code=400, detail=f"Unknown format: {fmt}")
        try:
            data = _analyze(payload).to_dict()
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        content = render(data, fmt)
        if fmt == "html":
            return HTMLResponse(content)
        media = {"json": "application/json", "markdown": "text/markdown"}[fmt]
        return PlainTextResponse(content, media_type=media)

    @app.post("/api/render/{fmt}")
    def render_report(fmt: str, payload: dict[str, Any] = Body(...)):
        """Render an already-computed report dict (e.g. a stored run)."""
        if fmt not in {"json", "html", "markdown"}:
            raise HTTPException(status_code=400, detail=f"Unknown format: {fmt}")
        data = payload.get("report")
        if not isinstance(data, dict):
            raise HTTPException(status_code=400, detail="Missing 'report' object.")
        content = render(data, fmt)
        if fmt == "html":
            return HTMLResponse(content)
        media = {"json": "application/json", "markdown": "text/markdown"}[fmt]
        return PlainTextResponse(content, media_type=media)

    # -- projects ------------------------------------------------------
    @app.get("/api/projects")
    def list_projects() -> list[dict[str, Any]]:
        return db.list_projects()

    @app.post("/api/projects")
    def create_project(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
        name = str(payload.get("name", "")).strip()
        if not name:
            raise HTTPException(status_code=400, detail="Project name is required.")
        config = {
            "detectors": payload.get("detectors"),
            "vault": payload.get("vault"),
            "custom_detectors": payload.get("custom_detectors"),
            "redact": payload.get("redact", True),
        }
        return db.create_project(
            name,
            agent_type=payload.get("agent_type", "generic"),
            description=payload.get("description", ""),
            config={k: v for k, v in config.items() if v is not None},
        )

    @app.get("/api/projects/{pid}")
    def get_project(pid: str) -> dict[str, Any]:
        p = db.get_project(pid)
        if not p:
            raise HTTPException(status_code=404, detail="Project not found")
        return p

    @app.patch("/api/projects/{pid}")
    def update_project(pid: str, payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
        p = db.update_project(
            pid,
            name=payload.get("name"),
            agent_type=payload.get("agent_type"),
            description=payload.get("description"),
            config=payload.get("config"),
        )
        if not p:
            raise HTTPException(status_code=404, detail="Project not found")
        return p

    @app.delete("/api/projects/{pid}")
    def delete_project(pid: str) -> dict[str, bool]:
        if not db.delete_project(pid):
            raise HTTPException(status_code=404, detail="Project not found")
        return {"deleted": True}

    @app.get("/api/projects/{pid}/connect")
    def connect_snippet(pid: str) -> dict[str, str]:
        project = db.get_project(pid)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return {
            "framework": registry.label_for(project["agent_type"]),
            "snippet": registry.snippet_for(project["agent_type"], project["name"]),
        }

    # -- runs ----------------------------------------------------------
    @app.get("/api/projects/{pid}/runs")
    def list_runs(pid: str) -> list[dict[str, Any]]:
        if not db.get_project(pid):
            raise HTTPException(status_code=404, detail="Project not found")
        return db.list_runs(pid)

    @app.post("/api/projects/{pid}/runs")
    def create_run(pid: str, payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
        project = db.get_project(pid)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        # Merge stored project settings with the request (request can't disable
        # detectors here; it just supplies the trace/scenario).
        settings = {**project["config"], **{k: payload[k] for k in ("detectors", "vault", "custom_detectors", "redact") if k in payload}}
        merged = {**settings, **{k: payload[k] for k in ("trace", "scenario_id") if k in payload}}
        try:
            result = _analyze(merged, project_name=project["name"])
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return db.create_run(pid, result.to_dict(), source=payload.get("source", "manual"))

    @app.get("/api/runs/{rid}")
    def get_run(rid: str) -> dict[str, Any]:
        run = db.get_run(rid)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        return run

    @app.delete("/api/runs/{rid}")
    def delete_run(rid: str) -> dict[str, bool]:
        if not db.delete_run(rid):
            raise HTTPException(status_code=404, detail="Run not found")
        return {"deleted": True}

    @app.post("/api/compare")
    def compare(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
        a = db.get_run(payload.get("a", ""))
        b = db.get_run(payload.get("b", ""))
        if not a or not b:
            raise HTTPException(status_code=404, detail="Run not found")
        pa, pb = _level_profile_ints(a["report"]), _level_profile_ints(b["report"])
        verdict = "a" if dominates(pa, pb) else ("b" if dominates(pb, pa) else "neither")
        return {"a": a, "b": b, "dominance": verdict}

    # -- SPA -----------------------------------------------------------
    index_file = _STATIC_DIR / "index.html"
    if index_file.exists():
        assets = _STATIC_DIR / "assets"
        if assets.exists():
            app.mount("/assets", StaticFiles(directory=str(assets)), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        def spa(full_path: str):
            # API routes above take precedence; unknown /api paths 404.
            if full_path.startswith("api/"):
                raise HTTPException(status_code=404, detail="Not found")
            candidate = _STATIC_DIR / full_path
            if full_path and candidate.is_file() and candidate.resolve().is_relative_to(_STATIC_DIR.resolve()):
                return FileResponse(candidate)
            return FileResponse(index_file)  # client-side routing
    else:  # pragma: no cover

        @app.get("/", response_class=HTMLResponse)
        def _not_built() -> str:
            return (
                "<h1>AgentLeak GUI not built</h1><p>Run <code>npm install &amp;&amp; npm run build</code> "
                "in <code>agentleak/web/frontend</code>, or reinstall the package.</p>"
            )

    return app


def run_server(host: str = "127.0.0.1", port: int = 8000, *, open_browser: bool = True) -> None:
    try:
        import uvicorn
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(_GUI_IMPORT_ERROR) from exc

    app = create_app()
    if open_browser:
        import threading
        import webbrowser

        threading.Timer(1.0, lambda: webbrowser.open(f"http://{host}:{port}")).start()
    uvicorn.run(app, host=host, port=port, log_level="warning")
