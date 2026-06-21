# Running agents (live & scripted)

A **run** can come from analyzing a trace you already have *or* from **executing
an agent** against a scenario and capturing the trace it produces. The second is
how you turn "I added a project" into "I tested a real agent against real
scenarios and got real results".

```
Scenario (task + private data)
        │   agentleak/agent/context.py  → RunContext
        ▼
Agent runs it  ──────────────►  Trace (what the agent actually did)
   agentleak/agent/runner.py
        │
        ▼
AgentRisk scoring (project's detectors + vault)  →  stored Run
```

## Two backends

| Backend | When | Needs |
| --- | --- | --- |
| **Scripted** (default) | offline demos, CI, no API key | nothing |
| **Live** | test a real model's behavior | an OpenAI-compatible endpoint + key |

The **scripted** agent deterministically fetches the records and discloses a
subset — useful to see the pipeline end-to-end. The **live** agent is a real LLM
given a toolbox; whether it leaks is the model's decision, so the result is a
genuine audit.

## Configure a live agent (per project)

Project → **Settings → Live agent endpoint**. Pick a preset or fill in:

- **Base URL** — any OpenAI-compatible `/v1` endpoint:
  - OpenAI `https://api.openai.com/v1`
  - OpenRouter `https://openrouter.ai/api/v1`
  - Ollama (local) `http://localhost:11434/v1`
  - vLLM / LM Studio / Together / Groq …
- **Model** — e.g. `gpt-4o-mini`, `openai/gpt-4o-mini`, `llama3.1`.
- **API key** — stored locally and **never returned by the API**. You can leave
  it blank and export `OPENAI_API_KEY` / `OPENROUTER_API_KEY` before launching.

> The key is the only thing that leaves redaction: it is write-only over the API
> (responses show `api_key_set: true`), and a blank key on save keeps the stored
> one.

## Run it

Project → **Audit → Run agent** → pick a scenario → **Run agent**. AgentLeak:

1. Builds the task + private records from the scenario (its stored **spec** if it
   has one, otherwise derived from its trace).
2. Runs the agent with these tools, recording each on its channel:

   | tool | channel |
   | --- | --- |
   | `get_records` | `tool_call` + `tool_response` (the data — a *source*) |
   | `save_memory` | `shared_memory` |
   | `send_message` | `inter_agent_message` |
   | `write_file` | `generated_file` |
   | `call_external_api` | `tool_call` |
   | `log_event` | `log` |
   | final reply | `final_output` |

3. Scores the captured trace with the project's detectors and vault scope and
   stores the run (`source` = `agent:<model>` or `agent:scripted`).

## From the API

```bash
curl -X POST http://127.0.0.1:8000/api/projects/$PID/execute \
  -H 'content-type: application/json' \
  -d '{"scenario_id": "agentleak_fin_00254", "mode": "live"}'
```

`mode` defaults to `live` when the project has an endpoint configured, else
`scripted`. The response is the stored run (with its full report).

## Notes

- Only the **live** run sends data to your endpoint — analysis is always local.
- Any scenario is runnable; imported AgentLeak **specs** give the richest task +
  vault, while plain traces are used to derive an equivalent task. See
  [Scenarios](scenarios.md).
- The LLM client is stdlib-only — AgentLeak adds **no dependency** for this.
