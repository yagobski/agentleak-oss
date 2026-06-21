"""Registry of agent frameworks.

The single source of truth for which agent frameworks AgentLeak supports, their
display labels, and the SDK connection snippet shown in the platform's *Connect*
tab. Adding a new framework is one :func:`register` call — it then appears in the
project agent-type picker and gets a Connect snippet automatically.

This mirrors how promptfoo treats plugins/providers as a registry rather than a
hardcoded list, but stays scoped to AgentLeak's trace-ingestion model.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

_HEAD = "# pip install 'agentleak'  ·  start the platform with: agentleak serve"


@dataclass(frozen=True)
class AgentFramework:
    id: str
    label: str
    snippet: Callable[[str], str]  # project_name -> python code
    docs: str = ""


_REGISTRY: dict[str, AgentFramework] = {}


def register(framework: AgentFramework) -> None:
    _REGISTRY[framework.id] = framework


def get(framework_id: str) -> AgentFramework | None:
    return _REGISTRY.get(framework_id)


def frameworks() -> list[dict[str, str]]:
    return [{"id": f.id, "label": f.label} for f in _REGISTRY.values()]


def framework_ids() -> list[str]:
    return list(_REGISTRY)


def label_for(framework_id: str) -> str:
    f = _REGISTRY.get(framework_id)
    return f.label if f else framework_id


def snippet_for(framework_id: str, project_name: str) -> str:
    f = _REGISTRY.get(framework_id) or _REGISTRY["generic"]
    return f.snippet(project_name)


# ----------------------------------------------------------------------
# Built-in frameworks
# ----------------------------------------------------------------------
def _generic(p: str) -> str:
    return f"""{_HEAD}
from agentleak import AgentLeakClient, capture, monitor

@monitor(channel="tool_call")
def call_tool(arg):
    return {{"customer_email": "test@example.com", "account_id": "ACC-12345"}}

client = AgentLeakClient(project={p!r})

with capture(run_id="run-001") as cap:
    call_tool(42)                    # your agent runs here

run = client.submit(cap.trace)       # appears in this project
print(run["risk_index"], run["verdict"])"""


def _langchain(p: str) -> str:
    return f"""{_HEAD}
from agentleak import AgentLeakClient
from agentleak.integrations.langchain import LangChainCallback

client = AgentLeakClient(project={p!r})
cb = LangChainCallback(run_id="run-001")

chain.invoke(inputs, config={{"callbacks": [cb]}})

run = client.submit(cb.trace)
print(run["risk_index"], run["verdict"])"""


def _langgraph(p: str) -> str:
    return f"""{_HEAD}
from agentleak import AgentLeakClient
from agentleak.integrations.langgraph import AgentLeakCallback

client = AgentLeakClient(project={p!r})
cb = AgentLeakCallback(run_id="run-001")

graph.invoke(inputs, config={{"callbacks": [cb]}})

run = client.submit(cb.trace)
print(run["risk_index"], run["verdict"])"""


def _crewai(p: str) -> str:
    return f"""{_HEAD}
from agentleak import AgentLeakClient
from agentleak.integrations.crewai import CrewAICallback

client = AgentLeakClient(project={p!r})
cb = CrewAICallback(run_id="run-001")

crew = Crew(agents=[...], tasks=[...],
            step_callback=cb.step_callback, task_callback=cb.task_callback)
crew.kickoff()

run = client.submit(cb.trace)
print(run["risk_index"], run["verdict"])"""


def _autogen(p: str) -> str:
    return f"""{_HEAD}
from agentleak import AgentLeakClient
from agentleak.integrations.autogen import trace_from_messages

client = AgentLeakClient(project={p!r})

trace = trace_from_messages(chat_result.chat_history, run_id="run-001")
run = client.submit(trace)
print(run["risk_index"], run["verdict"])"""


def _openai_agents(p: str) -> str:
    return f"""{_HEAD}
# OpenAI Agents SDK / Assistants — record your run as a generic trace.
from agentleak import AgentLeakClient
from agentleak.integrations.generic import TraceRecorder

client = AgentLeakClient(project={p!r})
rec = TraceRecorder(run_id="run-001")

rec.user_input(user_message)
rec.tool_call(tool_args, target=tool_name)        # for each tool call
rec.tool_response(tool_output, source=tool_name)  # for each tool result
rec.final_output(final_answer)

run = client.submit(rec.trace)
print(run["risk_index"], run["verdict"])"""


for _fw in (
    AgentFramework("generic", "Generic / SDK", _generic),
    AgentFramework("langchain", "LangChain", _langchain),
    AgentFramework("langgraph", "LangGraph", _langgraph),
    AgentFramework("crewai", "CrewAI", _crewai),
    AgentFramework("autogen", "AutoGen", _autogen),
    AgentFramework("openai_agents", "OpenAI Agents SDK", _openai_agents),
):
    register(_fw)
