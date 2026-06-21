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
from ..agent import AgentRunError, LLMConfig, OpenAICompatLLM, build_run_context, run_scenario
from ..core.agentrisk import dominates
from ..core.config import Config
from ..core.report import AnalysisResult
from ..core.runner import AgentLeakRunner
from ..core.store import Store
from ..core.trace import CHANNELS, Trace
from ..detectors import BUILTIN_DETECTORS
from ..integrations import registry
from ..reporters import render
from ..scenarios import SCENARIOS, list_scenarios, load_example_trace
from ..scenarios.convert import normalize_upload
from ..scenarios.packs import expand_pack, list_packs

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


def _trace_from_payload(payload: dict[str, Any], store: Store | None = None) -> Trace:
    sid = payload.get("scenario_id")
    if sid:
        try:
            return load_example_trace(sid)  # built-in
        except (KeyError, ValueError):
            pass
        if store is not None:
            stored = store.get_scenario(sid)
            if stored and stored.get("trace"):
                return Trace.from_dict(stored["trace"])
        raise ValueError(f"Unknown scenario '{sid}'.")
    trace = payload.get("trace")
    if not trace:
        raise ValueError("Provide a 'trace' object or a 'scenario_id'.")
    if isinstance(trace, str):
        trace = json.loads(trace)
    return Trace.from_dict(trace)


def _analyze(
    payload: dict[str, Any], *, project_name: str | None = None, store: Store | None = None
) -> AnalysisResult:
    data = _config_data(payload)
    if project_name:
        data["project"] = {"name": project_name}
    cfg = Config.from_dict(data) if data else None
    trace = _trace_from_payload(payload, store)
    return AgentLeakRunner(cfg).analyze(trace)


def _builtin_scenario_summary(scenario: Any) -> dict[str, Any]:
    """Normalize a built-in Scenario to the unified scenario-list shape."""
    d = scenario.to_dict()
    return {
        "id": d["id"],
        "name": d["id"],
        "domain": d["domain"],
        "description": d["description"],
        "sensitive_data": d["sensitive_data"],
        "expected_behavior": d["expected_behavior"],
        "tags": [],
        "difficulty": "",
        "source": "builtin",
        "builtin": True,
        "pack_id": "",
        "origin_id": "",
    }


def _level_profile_ints(report: dict[str, Any]) -> dict[int, int]:
    lp = report.get("summary", {}).get("level_profile", {})
    return {n: int(lp.get(f"L{n}", 0)) for n in (1, 2, 3, 4)}


def _safe_project(project: dict[str, Any] | None) -> dict[str, Any] | None:
    """Strip the agent API key from a project before returning it over HTTP."""
    if not project:
        return project
    config = project.get("config") or {}
    agent = config.get("agent")
    if isinstance(agent, dict) and "api_key" in agent:
        safe_agent = {**agent, "api_key": "", "api_key_set": bool(agent.get("api_key"))}
        return {**project, "config": {**config, "agent": safe_agent}}
    return project


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
        """Unified library: built-in scenarios first, then stored ones."""
        builtin = [_builtin_scenario_summary(s) for s in list_scenarios()]
        return builtin + db.list_scenarios()

    @app.post("/api/scenarios")
    def create_scenario(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
        """Create a scenario from an uploaded object (trace / spec / ai4privacy).

        Optional ``name``/``domain``/``description``/``tags`` override the values
        inferred from the upload.
        """
        source_obj = payload.get("data", payload.get("scenario", payload))
        if isinstance(source_obj, str):
            try:
                source_obj = json.loads(source_obj)
            except json.JSONDecodeError as exc:
                raise HTTPException(status_code=400, detail=f"Invalid JSON: {exc}") from exc
        try:
            meta, trace = normalize_upload(source_obj)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return db.create_scenario(
            payload.get("name") or meta["name"],
            trace.to_dict(),
            domain=payload.get("domain") or meta["domain"],
            description=payload.get("description") or meta["description"],
            sensitive_data=payload.get("sensitive_data") or meta["sensitive_data"],
            tags=payload.get("tags") or meta["tags"],
            difficulty=payload.get("difficulty") or meta.get("difficulty", ""),
            source="custom",
            spec=meta.get("spec"),
        )

    @app.get("/api/scenarios/{scenario_id}")
    def get_scenario_detail(scenario_id: str) -> dict[str, Any]:
        if scenario_id in SCENARIOS:
            summary = _builtin_scenario_summary(SCENARIOS[scenario_id])
            summary["trace"] = load_example_trace(scenario_id).to_dict()
            return summary
        stored = db.get_scenario(scenario_id)
        if not stored:
            raise HTTPException(status_code=404, detail="Scenario not found")
        return stored

    @app.delete("/api/scenarios/{scenario_id}")
    def delete_scenario(scenario_id: str) -> dict[str, bool]:
        if scenario_id in SCENARIOS:
            raise HTTPException(status_code=400, detail="Built-in scenarios cannot be deleted.")
        if not db.delete_scenario(scenario_id):
            raise HTTPException(status_code=404, detail="Scenario not found")
        return {"deleted": True}

    @app.get("/api/example/{scenario_id}")
    def example(scenario_id: str) -> dict[str, Any]:
        """A scenario's trace (built-in or stored) — used to seed the playground."""
        try:
            return load_example_trace(scenario_id).to_dict()
        except (KeyError, ValueError):
            stored = db.get_scenario(scenario_id)
            if stored and stored.get("trace"):
                return stored["trace"]
            raise HTTPException(status_code=404, detail="Scenario not found") from None

    # -- scenario packs ------------------------------------------------
    @app.get("/api/scenario-packs")
    def scenario_packs() -> list[dict[str, Any]]:
        packs = list_packs()
        for pack in packs:
            pack["imported_count"] = db.count_pack_scenarios(pack["id"])
        return packs

    @app.post("/api/scenario-packs/{pack_id}/import")
    def import_pack(pack_id: str) -> dict[str, Any]:
        try:
            entries = expand_pack(pack_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        imported, skipped = 0, 0
        for meta, trace in entries:
            origin = meta.get("origin_id", "") or ""
            if db.scenario_exists(pack_id, origin):
                skipped += 1
                continue
            db.create_scenario(
                meta["name"], trace.to_dict(),
                domain=meta["domain"], description=meta["description"],
                sensitive_data=meta["sensitive_data"], tags=meta["tags"],
                difficulty=meta.get("difficulty", ""),
                source="imported", pack_id=pack_id, origin_id=origin,
                spec=meta.get("spec"),
            )
            imported += 1
        return {"imported": imported, "skipped": skipped, "pack_id": pack_id}

    @app.get("/api/stats")
    def stats() -> dict[str, Any]:
        return db.stats()

    # -- stateless playground analysis ---------------------------------
    @app.post("/api/analyze")
    def analyze(payload: dict[str, Any] = Body(...)) -> JSONResponse:
        try:
            result = _analyze(payload, store=db)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return JSONResponse(result.to_dict())

    @app.post("/api/report/{fmt}")
    def report(fmt: str, payload: dict[str, Any] = Body(...)):
        if fmt not in {"json", "html", "markdown"}:
            raise HTTPException(status_code=400, detail=f"Unknown format: {fmt}")
        try:
            data = _analyze(payload, store=db).to_dict()
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
        return [_safe_project(p) for p in db.list_projects()]  # type: ignore[misc]

    @app.post("/api/projects")
    def create_project(payload: dict[str, Any] = Body(...)) -> dict[str, Any] | None:
        name = str(payload.get("name", "")).strip()
        if not name:
            raise HTTPException(status_code=400, detail="Project name is required.")
        config = {
            "detectors": payload.get("detectors"),
            "vault": payload.get("vault"),
            "custom_detectors": payload.get("custom_detectors"),
            "redact": payload.get("redact", True),
            "agent": payload.get("agent"),
        }
        return _safe_project(db.create_project(
            name,
            agent_type=payload.get("agent_type", "generic"),
            description=payload.get("description", ""),
            config={k: v for k, v in config.items() if v is not None},
        ))

    @app.get("/api/projects/{pid}")
    def get_project(pid: str) -> dict[str, Any] | None:
        p = db.get_project(pid)
        if not p:
            raise HTTPException(status_code=404, detail="Project not found")
        return _safe_project(p)

    @app.patch("/api/projects/{pid}")
    def update_project(pid: str, payload: dict[str, Any] = Body(...)) -> dict[str, Any] | None:
        config = payload.get("config")
        # Preserve a previously-stored agent key when the client sends a blank one.
        if isinstance(config, dict) and isinstance(config.get("agent"), dict):
            if not config["agent"].get("api_key"):
                existing = db.get_project(pid) or {}
                prior = (existing.get("config") or {}).get("agent") or {}
                if prior.get("api_key"):
                    config["agent"]["api_key"] = prior["api_key"]
        p = db.update_project(
            pid,
            name=payload.get("name"),
            agent_type=payload.get("agent_type"),
            description=payload.get("description"),
            config=config,
        )
        if not p:
            raise HTTPException(status_code=404, detail="Project not found")
        return _safe_project(p)

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
            result = _analyze(merged, project_name=project["name"], store=db)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return db.create_run(pid, result.to_dict(), source=payload.get("source", "manual"))

    def _scenario_detail(sid: str) -> dict[str, Any] | None:
        if sid in SCENARIOS:
            detail = _builtin_scenario_summary(SCENARIOS[sid])
            detail["trace"] = load_example_trace(sid).to_dict()
            detail["spec"] = None
            return detail
        return db.get_scenario(sid)

    @app.post("/api/projects/{pid}/execute")
    def execute_agent(pid: str, payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
        """Run the project's agent against a scenario and store the captured run."""
        project = db.get_project(pid)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        scenario = _scenario_detail(str(payload.get("scenario_id", "")))
        if not scenario:
            raise HTTPException(status_code=404, detail="Scenario not found")

        ctx = build_run_context(scenario)
        if not ctx.has_data:
            raise HTTPException(
                status_code=400,
                detail="This scenario has no private data for an agent to handle.",
            )

        agent_cfg = (project["config"] or {}).get("agent") or {}
        mode = payload.get("mode") or ("live" if agent_cfg.get("model") else "scripted")
        llm = None
        if mode == "live":
            if not agent_cfg.get("base_url") or not agent_cfg.get("model"):
                raise HTTPException(
                    status_code=400,
                    detail="Configure the agent endpoint (base URL + model) in project Settings first.",
                )
            llm = OpenAICompatLLM(LLMConfig(
                base_url=str(agent_cfg["base_url"]),
                model=str(agent_cfg["model"]),
                api_key=str(agent_cfg.get("api_key", "")),
            ))
        try:
            trace = run_scenario(ctx, llm=llm)
        except AgentRunError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        data = _config_data(project["config"])
        data["project"] = {"name": project["name"]}
        cfg = Config.from_dict(data) if data else None
        result = AgentLeakRunner(cfg).analyze(trace)
        source = f"agent:{llm.model}" if llm else "agent:scripted"
        return db.create_run(pid, result.to_dict(), source=source)

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
