# The platform — projects, runs & SDK

`agentleak serve` is a full local platform, not just a one-off auditor. It runs
entirely on your machine; projects and runs are stored in SQLite under
`$AGENTLEAK_HOME` (default `~/.agentleak`).

```bash
pip install 'agentleak[gui]'
agentleak serve            # http://127.0.0.1:8000
```

## Concepts

- **Project** — an agent you audit over time. It has a name, an *agent
  framework* (generic / LangChain / LangGraph / CrewAI / AutoGen), and a config
  (which detectors, the vault scope, custom rules, redaction).
- **Run** — one stored analysis of a project. Each run keeps the full AgentRisk
  report; you can view, export, compare, and delete runs.

## Pages

- **Dashboard** — projects, runs, average Risk Index, blocked-run count, recent runs.
- **Projects** — create and open projects.
- **Project → Audit** — run a scenario or pasted trace using the project's config.
- **Project → Runs** — history + **Compare** two runs (weight-robust dominance).
- **Project → Connect** — copy-paste SDK snippet for that agent framework.
- **Project → Settings** — edit detectors, vault, custom rules, redaction.
- **Playground** — score a trace instantly, nothing saved.
- **Scenarios** — the built-in synthetic scenario library.

## Connect an agent via the SDK

Create a project (UI or SDK), then push traces from your agent code. Runs appear
in the platform under that project.

```python
from agentleak import AgentLeakClient, capture, monitor

@monitor(channel="tool_call")
def call_crm(customer_id):
    return {"customer_email": "test@example.com", "account_id": "ACC-12345"}

client = AgentLeakClient(project="support-bot")   # get-or-create by name

with capture(run_id="run-001") as cap:
    call_crm(42)                                   # your agent runs here

run = client.submit(cap.trace)                     # stored under "support-bot"
print(run["risk_index"], run["verdict"])
```

Framework adapters work the same way — e.g. LangChain:

```python
from agentleak import AgentLeakClient
from agentleak.integrations.langchain import LangChainCallback

client = AgentLeakClient(project="support-bot")
cb = LangChainCallback(run_id="run-001")
chain.invoke(inputs, config={"callbacks": [cb]})
client.submit(cb.trace)
```

The **Connect** tab in each project shows the exact snippet for its framework.

## API (all local)

| Method | Path | Purpose |
| --- | --- | --- |
| GET/POST | `/api/projects` | list / create projects |
| GET/PATCH/DELETE | `/api/projects/{id}` | read / update / delete a project |
| GET/POST | `/api/projects/{id}/runs` | list / create runs |
| GET/DELETE | `/api/runs/{id}` | read / delete a run |
| POST | `/api/compare` | dominance comparison of two runs |
| GET | `/api/stats` | dashboard aggregates |
| POST | `/api/analyze` | stateless analysis (playground) |
| POST | `/api/render/{fmt}` | render a stored report to json/html/markdown |

## Data location

Everything is local. Point `AGENTLEAK_HOME` elsewhere to relocate the database:

```bash
AGENTLEAK_HOME=/path/to/data agentleak serve
```
