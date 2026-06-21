# Concepts

AgentLeak has a deliberately small vocabulary: **traces**, **events**,
**channels**, **detectors**, **findings**, and a **score**.

## Trace

A `Trace` is a normalized recording of one agent run. Everything — framework
callbacks, JSON files, SDK calls — is converted into this single format, so the
detection engine never deals with framework-specific structures.

```json
{
  "run_id": "run_001",
  "agent_name": "patient_summary_agent",
  "scenario_id": "healthcare_patient_summary",
  "events": [ ... ]
}
```

## Event

An `Event` is one observable thing that happened, on a specific **channel**:

```json
{
  "event_id": "evt_002",
  "channel": "tool_call",
  "source": "orchestrator",
  "target": "ehr_database",
  "content": { "patient_name": "Jean Tremblay", "nam": "TREM12345678" },
  "metadata": { "tool_name": "get_patient_record" }
}
```

`content` can be a string or a structured object. Structured content is
flattened into readable `key: value` text for detection, so both pattern
detectors and keyword detectors work on tool arguments.

## Channels

The eight normalized channels:

| Channel | What it is |
| --- | --- |
| `user_input` | what the user gave the agent (baseline — not a leak) |
| `final_output` | the answer returned to the user |
| `inter_agent_message` | messages passed between agents |
| `shared_memory` | values written to shared/persistent memory |
| `tool_call` | arguments sent to a tool |
| `tool_response` | data returned by a tool |
| `log` | framework / application logs |
| `generated_file` | files or documents the agent produced |

The product thesis: the **internal** channels (tool calls, memory, logs) are
where the real leakage happens, and output-only audits miss it.

## Detectors

A detector scans text and emits matches. Built-ins: `pii`, `secrets`,
`healthcare`, `finance`, `hr`, plus custom regex rules. They are pure regex +
dictionaries — no LLM, no network, fully explainable.

## Finding

A `Finding` is one detected leak with full context, including its AgentRisk
severity `level` (1–4):

```json
{
  "finding_id": "finding_001",
  "channel": "tool_call",
  "data_type": "health_identifier",
  "level": 4,
  "level_label": "L4",
  "severity": "critical",
  "confidence": 0.85,
  "redacted_value": "TR********78",
  "detector": "healthcare_nam_detector",
  "recommendation": "Remove or mask health identifiers before calling external tools."
}
```

Reports show the **redacted** value by default; the raw value is never written
unless you explicitly disable redaction.

## Score

Findings are combined into the **AgentRisk Risk Index** (`RI ∈ [0,1]`), a
per-channel RI breakdown, an L1–L4 severity profile, and a derived 0–100 privacy
score with a verdict. See [Scoring](scoring.md).
