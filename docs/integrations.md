# Integrations

AgentLeak analyzes a `Trace`. You can produce one in four ways, from least to
most automated.

## 1. By hand / from JSON

Write a trace JSON file and run `agentleak run --trace trace.json`. See
[Concepts](concepts.md) for the format.

## 2. SDK trace builder

```python
from agentleak import Trace, AgentLeakRunner

trace = Trace(run_id="run_001", agent_name="my_agent")
trace.add_event(channel="tool_call", source="agent", target="crm",
                content={"customer_email": "test@example.com"})
trace.add_event(channel="final_output", content="Done.")

result = AgentLeakRunner().analyze(trace)
```

## 3. The `@monitor` decorator

Record live calls without restructuring your code. It's a no-op outside a
`capture()` block, so it's safe to leave in place.

```python
from agentleak import capture, monitor

@monitor(channel="tool_call")
def call_crm(customer_id):
    return crm.get_customer(customer_id)

with capture(run_id="run_001") as cap:
    call_crm(42)

result = cap.analyze()
```

## 4. Framework adapters

None of these import their target framework at module load time, so importing
them is always safe.

### LangChain

```python
from agentleak.integrations.langchain import LangChainCallback

cb = LangChainCallback(run_id="run_001")
chain.invoke(inputs, config={"callbacks": [cb]})
result = cb.analyze()
```

Maps `on_tool_start`→`tool_call`, `on_tool_end`→`tool_response`,
`on_llm_end`→`final_output`, `on_agent_action`→`inter_agent_message`,
`on_text`→`log`.

### LangGraph

```python
from agentleak.integrations.langgraph import AgentLeakCallback, trace_from_state

cb = AgentLeakCallback(run_id="run_001")
graph.invoke(inputs, config={"callbacks": [cb]})
result = cb.analyze()

# or ingest a final graph state:
trace = trace_from_state(final_state, run_id="run_001")
```

### CrewAI

```python
from agentleak.integrations.crewai import CrewAICallback

cb = CrewAICallback(run_id="run_001")
crew = Crew(agents=[...], tasks=[...],
            step_callback=cb.step_callback, task_callback=cb.task_callback)
crew.kickoff()
result = cb.analyze()
```

### AutoGen

```python
from agentleak.integrations.autogen import trace_from_messages
from agentleak import AgentLeakRunner

trace = trace_from_messages(chat_result.chat_history, run_id="run_001")
result = AgentLeakRunner().analyze(trace)
```

### Anything else

Use the generic recorder and map your framework's events onto channels:

```python
from agentleak.integrations.generic import TraceRecorder
from agentleak import AgentLeakRunner

rec = TraceRecorder(run_id="run_001")
rec.tool_call({"ssn": "123-45-6789"}, target="db")
rec.shared_memory("cached customer record ...")
rec.final_output("All set!")

result = AgentLeakRunner().analyze(rec.trace)
```
