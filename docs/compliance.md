# Compliance frameworks

Every AgentLeak report maps its findings to the controls of the regulatory and
security frameworks privacy auditors care about, so you can see *which controls a
run puts at risk*. It's the AgentLeak analogue of promptfoo's framework mappings,
scoped to privacy leakage and driven by the AgentRisk severity taxonomy.

> This flags controls to review — it is **not** legal certification.

## Frameworks

| Framework | Example controls AgentLeak maps to |
| --- | --- |
| **GDPR** (EU 2016/679) | Art. 5(1)(c) minimisation · Art. 5(1)(f) confidentiality · Art. 9 special category · Art. 32 security |
| **Québec Law 25** | Sensitive personal information · Confidentiality by default |
| **NIST AI RMF** (AI 100-1) | MEASURE 2.7 privacy measured · Privacy-Enhanced characteristic · MANAGE 1.3 risk treated |
| **OWASP LLM Top 10** (2025) | LLM02 Sensitive Information Disclosure · LLM06 Excessive Agency |
| **EU AI Act** (2024/1689) | Art. 10 Data governance |

## How it works

Each control is a small, explainable predicate over the **leaked** findings:

- **severity levels** leaked (L1–L4),
- **data types** leaked (e.g. health, credentials),
- **channels** leaked on (tool_call, log, …),
- the run's **Risk Index** and whether it's **blocked**.

A control returns *evidence* (the data types / channels / levels that triggered
it); empty evidence means compliant. Example: a leaked health identifier trips
**GDPR Art. 9** with evidence `health_identifier`; a leaked AWS key trips **GDPR
Art. 32**; an elevated Risk Index trips **NIST – Privacy-Enhanced**.

The result appears in:

- the **web UI** (a Compliance section on every run, framework cards with
  per-control status),
- the **HTML / Markdown exports**,
- the **CLI** summary line (`Compliance: 3/5 frameworks clear …`),
- the **JSON report** under `compliance` (for CI gating).

## Add or adjust a framework

Frameworks live in [`agentleak/core/compliance.py`](../agentleak/core/compliance.py)
as data. Append a `Framework` with `Control`s — each control's `detect(ctx)`
returns evidence tokens (empty = compliant). Add a case to
`tests/test_compliance.py`. See [AGENTS.md](../AGENTS.md) §6c.
