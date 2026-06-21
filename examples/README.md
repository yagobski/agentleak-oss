# Examples

## Trace files

Five synthetic traces, one per built-in scenario. Analyze any of them:

```bash
agentleak run --trace examples/healthcare_trace.json
agentleak run --trace examples/finance_trace.json --format html
```

| File | Scenario |
| --- | --- |
| `healthcare_trace.json` | healthcare patient summary |
| `finance_trace.json` | loan application review |
| `hr_trace.json` | employee HR case |
| `education_trace.json` | school document publication |
| `customer_support_trace.json` | CRM support request |

All data is fictional.

## Runnable Python scripts

```bash
python examples/simple_agent.py          # SDK trace builder
python examples/multiagent_pipeline.py   # generic recorder, multi-agent shape
```
