# AGENTS.md — guide for AI agents & contributors working on AgentLeak OSS

This file is the map of the codebase and the rules for changing it safely. Read
it before editing. It is written for both human contributors and AI coding
agents. (Human-facing usage docs live in [README.md](README.md) and [docs/](docs/).)

---

## 1. What this is

**AgentLeak OSS** is a local, dependency-light tool that tests whether an AI
agent leaks sensitive data across its execution channels — tool calls, shared
memory, inter-agent messages, logs, generated files — not just its final answer.

Leakage is scored with **AgentRisk**, a severity-weighted, density-normalized
**Risk Index** `RI ∈ [0,1]` grounded in GDPR Article 9 and Québec Law 25. It is
the practical scoring layer from the AgentRisk paper; the implementation in
[`agentleak/core/agentrisk.py`](agentleak/core/agentrisk.py) reproduces the
paper's worked example exactly and is verified against the paper's five formal
properties.

**Non-negotiable product values** (do not regress these):
- **Local only.** No network calls, no telemetry, no LLM dependency in the core.
- **Explainable.** Detection is regex + dictionaries. Scoring is a closed-form
  formula. No black boxes.
- **Privacy-first.** Reports redact values by default; raw values are never
  written unless explicitly opted out. The HTML report and the GUI are fully
  self-contained (no CDN, self-hosted fonts).

---

## 2. Data flow (the mental model)

```
Trace (events on channels)
   │   agentleak/core/trace.py
   ▼
Detectors  ── regex/dict ──▶  RawMatch        agentleak/detectors/*
   │   (each event's searchable_text)
   ▼
Runner: RawMatch + event context + AgentRisk level ──▶ Finding
   │   agentleak/core/runner.py  (level via agentrisk.level_for)
   ▼
AgentRisk scoring: WSL, ρ_S, RI, per-channel RI, level profile
   │   agentleak/core/agentrisk.py  →  agentleak/core/scoring.py (Score)
   ▼
AnalysisResult  ──▶  reporters (json/html/markdown)  +  web GUI
       agentleak/core/report.py        agentleak/reporters/*   agentleak/web/*
```

Everything funnels through `AgentLeakRunner.analyze(trace)`. The CLI, the SDK,
the framework integrations, and the web API all call it.

---

## 3. Repository layout

```
agentleak/
├── __init__.py            Public SDK surface (Trace, AgentLeakRunner, etc.)
├── cli.py                 Typer CLI: init/run/report/validate/scenarios/serve/version
├── core/
│   ├── trace.py           Trace + Event + Channel; content_to_text() flattening
│   ├── detector.py        Detector base, RawMatch, Finding, Severity, redact()
│   ├── agentrisk.py       ★ AgentRisk scoring: taxonomy, RI, properties
│   ├── scoring.py         Score dataclass; wraps agentrisk for the runner
│   ├── runner.py          AgentLeakRunner — the one orchestration seam
│   ├── report.py          AnalysisResult + to_dict() (the report schema)
│   ├── config.py          agentleak.yaml model + DEFAULT_CONFIG_YAML
│   ├── store.py           ★ SQLite store: projects + runs ($AGENTLEAK_HOME)
│   ├── compliance.py      ★ map findings -> GDPR/Law25/NIST AI RMF/OWASP/EU AI Act
│   └── scenario.py        Scenario dataclass
├── client.py              ★ AgentLeakClient — push traces from an agent (stdlib urllib)
├── agent/                 ★ live agent runner: execute a real LLM agent vs a scenario
│   ├── context.py         RunContext (from a stored spec, or derived from a trace)
│   ├── llm.py             OpenAI-compatible chat client (stdlib urllib; optional)
│   └── runner.py          agentic loop -> Trace (live) + scripted offline fallback
├── detectors/             pii, secrets, healthcare, finance, hr, custom + registry
├── scenarios/             5 built-in scenarios + bundled example traces loader
│   ├── convert.py         ★ external formats (AgentLeak spec / ai4privacy) -> traces
│   └── packs/             ★ importable scenario packs (JSON bundles + loader)
├── examples/              Synthetic trace JSON (the scenarios' fixtures)
├── reporters/             json/html/markdown renderers + report.html.j2 template
├── integrations/          generic (TraceRecorder) + langchain/langgraph/crewai/autogen
│   └── registry.py        ★ pluggable agent-framework registry (+ SDK snippets)
└── web/
    ├── app.py             FastAPI: /api/* (analyze, projects, runs, compare, stats) + SPA
    ├── static/            ★ BUILT frontend bundle (committed; served at runtime)
    └── frontend/          React + Vite + Tailwind + shadcn/ui SOURCE (dev only)
        └── src/
            ├── lib/        api.ts (typed client), format.ts, agents.ts (SDK snippets)
            ├── components/ui/  shadcn primitives
            ├── features/   RiGauge, ResultsView, ConfigPanel, RunRow, ThemeToggle
            ├── layout/     AppShell (sidebar nav)
            └── pages/      Dashboard, Projects, ProjectDetail, RunView, Playground, ...
tests/                     pytest; conftest isolates $AGENTLEAK_HOME; test_agentrisk conformance
docs/                      quickstart, concepts, scoring, scenarios, integrations, gui, platform
```

`★` = the files most likely to matter when extending the product.

---

## 4. AgentRisk — the scoring you must understand before touching scoring

Full reference: [docs/scoring.md](docs/scoring.md). The essentials:

```
WSL = Σ w(level(s))   over distinct LEAKED secrets s
ρ_S = Σ w(level(s))   over the audited vault S
RI  = WSL / ρ_S       ∈ [0, 1]
privacy_score = round(100 × (1 − RI))
```

- **Four-tier taxonomy** (`DATA_TYPE_LEVELS` in `agentrisk.py`): L1=1 (identifiers),
  L2=2 (contact/behavioral), L3=3 (financial/legal/DOB/address), L4=4 (health,
  SIN/SSN, cards, credentials). Each detector `data_type` maps to a level.
- **Distinct secrets, not occurrences.** A secret repeated on 3 channels counts
  once in global WSL; per-channel RI still localizes it.
- **Sources vs disclosures** — `BASELINE_CHANNELS = {user_input, tool_response}`.
  Data flowing *into* the agent (the user's input, a tool's response) populates
  the vault but is **not a leak**. The agent leaks via what it *emits*: tool_call
  args, shared_memory, inter_agent_message, log, generated_file, final_output.
  **If you change this set, every score changes** — update tests and docs.
- **The vault (ρ_S)** defaults to the observed reachable set (all distinct
  secrets detected). An explicit vault (`config.vault` / `analyze(vault=...)`)
  gives a deployment-accurate denominator that also counts non-leaked secrets.
- **Five properties** (in `tests/test_agentrisk.py`): boundedness, monotonicity,
  severity sensitivity, scale invariance, rank robustness under dominance. Any
  change to scoring must keep these green.

---

## 5. Invariants & gotchas (read before editing)

1. **`Finding.level` (1–4) is the privacy axis; `Finding.severity`
   (low/med/high/critical) is a secondary detector signal.** Scoring and the UI
   lead with `level`. New data types need an entry in `DATA_TYPE_LEVELS`,
   otherwise they fall back to a severity→level guess.
2. **`content_to_text()` flattens dict content into `key: value` text** (with
   underscores→spaces) so keyword-anchored detectors work on tool arguments.
   Don't "simplify" it to `json.dumps` — that breaks finance/HR detection.
3. **The report's `findings` array contains LEAKS only** (`leaked_findings()`),
   while `AnalysisResult.findings` holds *all* detections (sources included, used
   to build the vault). Keep that distinction.
4. **Redaction**: `Finding.to_dict(redact_values=True)` omits `matched_value`.
   Never log or persist raw values by default.
5. **Detectors must be pure** (regex/dict only, no I/O, no network, no LLM).
6. **The GUI is a built artifact.** Editing `agentleak/web/frontend/**` requires
   a rebuild (`npm run build` → `agentleak/web/static/`). The committed
   `static/` bundle is what `pip install` ships and what FastAPI serves. The
   `frontend/` source is excluded from the wheel.
7. **No emoji in code; ASCII identifiers.** (`ρ_S` appears only in display
   strings, never code identifiers.)
8. **Frontend API calls MUST be absolute (`/api/...`).** Relative paths
   (`api/...`) resolve against the current route and break on deep links like
   `/projects/:id`. All calls go through `lib/api.ts` — keep them absolute.
9. **The platform store lives at `$AGENTLEAK_HOME`** (default `~/.agentleak`,
   SQLite). Tests must never touch the real dir — `tests/conftest.py` points
   `AGENTLEAK_HOME` at a temp dir for the whole session; web/store tests also pass
   an explicit `Store(tmp)`.
10. **The SPA is served by a catch-all** in `web/app.py` (`/{full_path:path}` →
    `index.html`) so BrowserRouter deep links work; `/assets` is a separate mount
    and `/api/*` routes are registered first so they take precedence.
11. **`scenarios/packs/` is a package, not a module.** `importlib.resources`
    locates the bundled pack JSONs by package name, so the loader lives in
    `packs/__init__.py` — never add a sibling `packs.py` (it shadows the package
    and breaks `resources.files`). Pack JSONs are force-included in the wheel via
    `pyproject.toml` `[tool.hatch.build.targets.wheel].artifacts`.
12. **The LLM stays optional and out of the core.** `agentleak/agent/llm.py` is
    stdlib-only and is only invoked on an explicit live run; nothing in the
    analysis path imports it implicitly. Never make the core depend on a model.
    Agent API keys are secrets: redact them in responses (`_safe_project`) and
    never log them.
13. **Store migrations are additive.** `_init` uses `CREATE TABLE IF NOT EXISTS`;
    new columns on existing tables go through `_migrate` (PRAGMA-checked
    `ALTER TABLE ADD COLUMN`) so older local DBs keep working. `_scenario_row`
    tolerates a missing `spec` column for the same reason.

---

## 6. How to extend

### Add a detector
1. Subclass `Detector` in `agentleak/detectors/<name>.py`; set `name`; implement
   `detect(text) -> list[RawMatch]`. Use `self._match(...)`.
2. Register it in `agentleak/detectors/__init__.py` (`BUILTIN_DETECTORS`).
3. Map each new `data_type` to a level in `agentrisk.DATA_TYPE_LEVELS`.
4. Add a config toggle field in `core/config.py:DetectorToggles` if it's a
   built-in.
5. Tests in `tests/test_detectors.py`: a positive case **and** a clean-text
   guard (no false positives).

### Add a scenario
1. Define a `Scenario` under `agentleak/scenarios/<domain>.py`.
2. Bundle a **synthetic** trace in `agentleak/examples/<id>_trace.json`. Make it
   realistic: agent *receives* a full record via `tool_response`, leaks a
   *subset* onto disclosure channels, keeps `final_output` clean.
3. Register it in `agentleak/scenarios/__init__.py`.
4. Add it to `tests/test_scenarios.py` (it asserts every example loads, leaks,
   and keeps the final output clean).

### Add a scenario pack
Drop a JSON file in `agentleak/scenarios/packs/` (`{id, name, source, format,
scenarios: [...]}`). Entries may be AgentLeak specs, ai4privacy records, or raw
traces — `normalize_upload` auto-detects each. Every bundled scenario must
**leak** under the detectors (see `tests/test_packs.py`); filter out-of-scope
records when generating the pack. The wheel artifacts glob already includes
`agentleak/scenarios/packs/*.json`.

### Support a new upload format
Add a branch to `detect_format` and a converter in `scenarios/convert.py`,
wire it into `normalize_upload`, and cover it in `tests/test_convert.py`. Keep
converters pure and deterministic.

### Add a framework integration
Subclass `agentleak/integrations/generic.py:TraceRecorder` and translate the
framework's callbacks into `record(channel, content, ...)`. Never import the
framework at module top-level (lazy-import inside methods) so the package always
imports.

### Add a GUI feature
Source: `agentleak/web/frontend/src/`. Components: `components/ui/*` (shadcn
primitives), `features/*` (app views), `lib/api.ts` (typed client), `lib/format.ts`
(verdict/severity styling). After editing, `npm run build` then reinstall. See §7.

---

## 6b. The platform (projects, runs, SDK)

On top of the stateless analyzer, AgentLeak is a local **platform**:

- **Projects** (`core/store.py`) — each is an agent under test: a name, an
  `agent_type` (for SDK snippets), and a `config` (detectors / vault / custom
  rules / redact). Persisted in SQLite under `$AGENTLEAK_HOME`.
- **Runs** — every analysis of a project is stored (full report + denormalized
  `risk_index`/`verdict`/`blocked` for fast listing). Viewed, compared
  (`dominates()` from agentrisk), exported, deleted.
- **SDK client** (`client.py`) — `AgentLeakClient(project="...")` lets an agent
  `submit(trace)` to a running `agentleak serve`; the run shows up in the UI.
  The **Connect** tab generates the right snippet per `agent_type`
  (`frontend/src/lib/agents.ts`).
- **API** (`web/app.py`): `GET/POST /api/projects`, `GET/PATCH/DELETE
  /api/projects/{id}`, `GET/POST /api/projects/{id}/runs`, `GET/DELETE
  /api/runs/{id}`, `POST /api/compare`, `GET /api/stats`, plus the stateless
  `/api/analyze` and `/api/render/{fmt}` (render a stored report).

To add a platform feature: extend `Store` (+ `tests/test_store.py`), add the
endpoint in `web/app.py` (+ `tests/test_platform.py`), add the typed method in
`frontend/src/lib/api.ts`, then build the page/route. Keep it local-only.

## 6c. Compliance frameworks & the agent registry

**Compliance** (`core/compliance.py`). `evaluate(report_dict)` maps the leaked
findings to controls across GDPR, Québec Law 25, NIST AI RMF, the OWASP LLM Top
10, and the EU AI Act. Each control is a small predicate over a `Ctx`
(leaked_levels / data_types / channels / risk_index / blocked) returning
*evidence tokens* — empty means compliant. It is computed once in
`AnalysisResult.to_dict()` and embedded as `report["compliance"]`, so every
stored run and every export carries it. To add a framework or control, append to
`FRAMEWORKS` and add a case to `tests/test_compliance.py`. This is intentionally
a *flagging* tool, not legal certification.

**Agent registry** (`integrations/registry.py`). The single source of truth for
supported agent frameworks: `id`, `label`, and a `snippet(project_name)` SDK
example. `store.AGENT_TYPES`, `/api/meta`'s `agent_types`, and the project
*Connect* tab all read from it. **Adding a framework = one `register()` call**
(plus an optional adapter in `integrations/<name>.py`); it then appears in the
agent-type pickers and gets a Connect snippet automatically. The frontend never
hardcodes the framework list — selects come from `/api/meta`, snippets from
`/api/projects/{id}/connect`.

## 6d. The scenario library (upload, packs, conversion)

The **Scenarios** page is a managed library, not a static list. It merges the
five packaged `Scenario`s (read-only, `source: builtin`) with user scenarios
persisted in the store (`source: custom` for uploads, `source: imported` for
pack imports).

- **Conversion** (`scenarios/convert.py`). The analyzer consumes *traces*, but
  external datasets don't carry one. `normalize_upload(data)` auto-detects the
  format (`detect_format`) — an AgentLeak trace, an AgentLeak scenario *spec*
  (objective + `private_vault`), an ai4privacy PII record, or an OSS scenario
  object — and returns `(metadata, Trace)`. For specs/records it **synthesizes**
  a leaky trace: the record arrives via `tool_response` (a source, not a leak),
  then a subset leaks across disclosure channels; volume scales with the
  scenario's adversary level (A0<A1<A2). Pure & deterministic.
- **Packs** (`scenarios/packs/`). A *package* (not a module — see invariant 11)
  of JSON bundles + a loader. `list_packs()` / `expand_pack(id)` convert every
  entry via `normalize_upload`. Two ship: `agentleak_bench` (36 curated AgentLeak
  scenarios) and `ai4privacy_probes` (17 PII records). Add a pack = drop a JSON
  file here (force-included in the wheel via `pyproject.toml` artifacts).
- **Store** (`store.create_scenario` / `list_scenarios` / `get_scenario` /
  `delete_scenario` / `scenario_exists` / `count_pack_scenarios`). Imports are
  idempotent on `(pack_id, origin_id)`.
- **API** (`web/app.py`): `GET/POST /api/scenarios`, `GET/DELETE
  /api/scenarios/{id}`, `GET /api/scenario-packs`,
  `POST /api/scenario-packs/{id}/import`. `GET /api/example/{id}` and the
  `scenario_id` field of `/api/analyze` & runs resolve **both** built-in and
  stored scenarios (`_trace_from_payload` checks built-in first, then the store).

## 6e. Live agent execution (run a real agent against a scenario)

A *run* can now come from actually **executing an agent**, not just analyzing a
pre-made trace. `agentleak/agent/`:

- `context.build_run_context(scenario)` → a `RunContext` (task + private records
  + privacy instruction). Uses a stored **spec** if present, else **derives** the
  task from the trace's `user_input` and the records from its `tool_response`
  events — so every scenario is runnable.
- `runner.run_scenario(ctx, llm=None)` → a `Trace`. With an `llm` it runs a real
  **agentic loop** (`_live_run`): the model is given a toolbox (`get_records`,
  `save_memory`, `send_message`, `write_file`, `call_external_api`, `log_event`)
  and every tool it calls is recorded on the matching channel; the final message
  is `final_output`. Whether it leaks is the model's choice — the audit is real.
  Without an `llm` it runs the deterministic `_scripted_run` (reuses
  `scenario_spec_to_trace`) for offline/CI use.
- `llm.OpenAICompatLLM` — a stdlib-only (`urllib`) chat-completions client for any
  OpenAI-compatible endpoint (OpenAI, OpenRouter, Ollama, vLLM…). **No new
  dependency; never imported by the core** — only reached when a user runs live.
  Key resolution: explicit config key → conventional env var.
- **API**: `POST /api/projects/{id}/execute` `{scenario_id, mode?}`. `mode`
  defaults to `live` if the project has an agent endpoint configured, else
  `scripted`. The project's detectors/vault score the captured trace; the run is
  stored with `source` = `agent:<model>` / `agent:scripted`.
- **Project agent config** lives in `project.config.agent` =
  `{base_url, model, api_key}`. The key is **redacted** in every API response
  (`_safe_project` → `api_key:"", api_key_set:bool`) and **preserved** on PATCH
  when the client sends a blank key.

## 7. Dev commands

```bash
# Python (run from repo root, in a venv)
pip install -e ".[dev]"          # core + gui + test deps
pytest                            # 196 tests
pytest --cov=agentleak --cov-fail-under=85   # CI gate is 85% (currently ~94%)
ruff check agentleak/ tests/      # lint (must be clean)
mypy agentleak/                   # types (must be clean)

# CLI
agentleak run --scenario healthcare_patient_summary
agentleak serve                   # GUI at http://127.0.0.1:8000

# Frontend (in agentleak/web/frontend/)
npm install
npm run dev                       # Vite dev server, proxies /api → :8000
                                  #   (run `agentleak serve` alongside it)
npm run build                     # type-check + build → ../static
```

**Round-trip when changing the GUI:** `npm run build` (in `frontend/`) → `pip
install .` (from repo root) → restart `agentleak serve`. FastAPI reads the static
dir per request, so a browser reload picks up a rebuild without a server restart
once the package is reinstalled.

---

## 8. Conventions

- Python ≥ 3.10, fully typed, `from __future__ import annotations`.
- `ruff` + `mypy` clean is required; CI enforces both plus ≥70% coverage.
- Detectors/scoring stay LLM-free and offline. Optional LLM detection, if ever
  added, must live behind an extra and never be a required dependency.
- Tests: detectors need false-positive guards; AgentRisk changes must keep the
  five conformance properties; the worked example (RI 0.238) is the golden test.
- The frontend uses shadcn/ui components (`components/ui/`), Tailwind tokens
  (`src/index.css`), self-hosted fonts (Hanken Grotesk + JetBrains Mono), and
  CSS-based enter animations that degrade safely (the rendered value is always
  the final value — see `RiGauge` / the `arc-draw`/`bar-grow` keyframes).
- The app shell follows the shadcn **blocks** dashboard pattern: `layout/AppShell.tsx`
  wraps everything in `SidebarProvider` → collapsible `Sidebar` (variant `inset`)
  + `SidebarInset` with a sticky `SiteHeader` (sidebar trigger + breadcrumb +
  theme toggle). Sidebar colors come from the `--sidebar-*` tokens (both themes).
  Pages render inside the inset and use `PageHeader` for their title/actions.

---

## 9. Where to look first for a given task

| Task | Start here |
| --- | --- |
| Change what counts as a leak | `agentrisk.BASELINE_CHANNELS`, `docs/scoring.md` |
| Tune severity levels | `agentrisk.DATA_TYPE_LEVELS` (+ `scoring.level_overrides`) |
| Add or fix a detector | `detectors/`, `tests/test_detectors.py` |
| Change the report schema | `core/report.py:to_dict` (+ reporters + `lib/api.ts`) |
| Change the HTML report | `reporters/templates/report.html.j2` |
| Change the GUI | `web/frontend/src/`, then rebuild (§7) |
| Add a page / route | `web/frontend/src/pages/`, `src/main.tsx` (router) |
| Change persistence | `core/store.py`, `tests/test_store.py` |
| Add a platform endpoint | `web/app.py`, `src/lib/api.ts`, `tests/test_platform.py` |
| Add an agent framework | `integrations/registry.py` (one `register()`; + optional adapter) |
| Add/change a compliance framework | `core/compliance.py:FRAMEWORKS`, `tests/test_compliance.py` |
| Add a scenario pack | drop JSON in `scenarios/packs/`, `tests/test_packs.py` |
| Support a new upload format | `scenarios/convert.py` (`detect_format` + converter), `tests/test_convert.py` |
| Change scenario persistence | `core/store.py` (scenarios table + `_migrate`), `tests/test_store.py` |
| Change how the live agent behaves | `agent/runner.py` (tools, loop), `tests/test_agent.py` |
| Add an LLM provider quirk | `agent/llm.py` (`_KEY_ENV_BY_HOST`, request shape) |
| Run an agent from the API | `web/app.py:execute_agent`, `tests/test_platform.py` |
| Add a CLI command | `cli.py`, `tests/test_cli.py` |
```
