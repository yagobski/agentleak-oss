# Changelog

All notable changes to AgentLeak OSS are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/), and the project adheres to
[Semantic Versioning](https://semver.org/).

## [0.6.0] — 2026-06-21

### Added
- **Leak flow & agent topology** (`core/flow.py`) — debugging views for
  multi-agent leaks:
  - **Leak paths**: each disclosed secret is traced from where it entered the
    system (a source channel) through every agent that handled it to each point
    of disclosure, so you can see exactly where a leak originated and how it
    propagated. Values stay redacted.
  - **Agent topology**: a behavioral graph of the agent — participants as nodes
    (inputs → agents → sinks), channels as edges, leak-carrying edges flagged by
    severity. Rendered as a diagram in the new **Leak flow** tab and embedded in
    the report (`report.flow` / `report.leak_paths`) and the Markdown export.

## [0.5.0] — 2026-06-21

Production-hardening release.

### Added
- **Release automation** — `release.yml` publishes the sdist + wheel to PyPI
  (Trusted Publishing) and attaches them to a GitHub Release on every `v*` tag.
- **Frontend CI** — a dedicated job type-checks and builds the web UI so a bad
  change can never ship a broken bundle.
- **CHANGELOG.md**.

### Changed
- Test suite expanded to **196 tests / 94% coverage**; the CI coverage gate was
  raised from 70% to **85%**. Hardened the newest code paths: the LLM client
  (59→98%), the CLI (79→90%), the SDK client (77→93%), and the LangChain adapter.

### Verified
- Clean-room wheel install (fresh venv): CLI, `run`, `serve` (GUI + API + SPA
  deep links) all functional.

## [0.4.1] — 2026-06-21

### Changed
- Adopted the official shadcn/ui **blocks** dashboard shell: collapsible sidebar
  (icon-collapse on desktop, drawer on mobile), sticky site header with route
  breadcrumb, and section-card dashboard. Light and dark themes.

## [0.4.0] — 2026-06-21

### Added
- **Live agent runner** — execute a real LLM agent (any OpenAI-compatible
  endpoint: OpenAI, OpenRouter, Ollama, vLLM) against a scenario and score the
  trace it actually produces. Deterministic scripted agent for offline/CI use.
  Per-project agent endpoint config; API keys are redacted in responses.
- Scenarios persist their original spec (objective + vault + tools) so they are
  runnable live; `POST /api/projects/{id}/execute`.
- **Tabbed run view**: Overview / Findings / Recommendations / Compliance.

## [0.3.0] — 2026-06-20

### Added
- **Scenario library** — search/filter, upload (AgentLeak traces, AgentLeak
  specs, or ai4privacy records — auto-detected & converted), and importable
  packs (AgentLeak Bench + PII Probes). One-click run in the playground.

## [0.2.0] — 2026-06-20

First public release.

### Added
- **AgentRisk** density-normalized Risk Index scoring (GDPR Art. 9 / Québec Law 25).
- Six detector families (PII, secrets, healthcare, finance, HR, custom regex)
  across eight execution channels.
- Five compliance frameworks (GDPR, Law 25, NIST AI RMF, OWASP LLM Top 10, EU AI Act).
- Pluggable agent-framework registry (LangChain / LangGraph / CrewAI / AutoGen /
  OpenAI Agents + generic).
- Local platform: SQLite persistence (projects + runs), SDK client, compare/stats.
- Web GUI (React + shadcn/ui), CLI (`init/run/report/validate/scenarios/serve`).

[0.6.0]: https://github.com/yagobski/agentleak-oss/releases/tag/v0.6.0
[0.5.0]: https://github.com/yagobski/agentleak-oss/releases/tag/v0.5.0
[0.4.1]: https://github.com/yagobski/agentleak-oss/releases/tag/v0.4.1
[0.4.0]: https://github.com/yagobski/agentleak-oss/releases/tag/v0.4.0
[0.3.0]: https://github.com/yagobski/agentleak-oss/releases/tag/v0.3.0
[0.2.0]: https://github.com/yagobski/agentleak-oss/releases/tag/v0.2.0
