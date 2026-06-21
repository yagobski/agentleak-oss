"""Integration adapter tests (no third-party frameworks required)."""

from __future__ import annotations

from agentleak import AgentLeakRunner
from agentleak.integrations.autogen import trace_from_messages
from agentleak.integrations.crewai import CrewAICallback
from agentleak.integrations.generic import TraceRecorder, from_events
from agentleak.integrations.langchain import LangChainCallback
from agentleak.integrations.langgraph import trace_from_state


def test_generic_recorder():
    rec = TraceRecorder(run_id="r")
    rec.tool_call({"email": "a@b.com"}, target="crm")
    rec.final_output("done")
    result = AgentLeakRunner().analyze(rec.trace)
    assert any(f.data_type == "email" for f in result.findings)


def test_from_events_builds_trace():
    trace = from_events([
        {"channel": "tool_call", "content": {"ssn": "123-45-6789"}},
        {"channel": "final_output", "content": "ok"},
    ], run_id="r")
    assert len(trace.events) == 2
    assert trace.events[0].event_id == "evt_001"


def test_langchain_callback_duck_typed():
    cb = LangChainCallback(run_id="r")
    cb.on_tool_start({"name": "crm"}, "lookup customer alex@example.com")
    cb.on_tool_end("account ACC-99887")
    cb.on_text("INFO processed for alex@example.com")
    result = cb.analyze()
    channels = {f.channel for f in result.findings}
    assert "tool_call" in channels
    assert "log" in channels


def test_langchain_agent_action_and_llm_end():
    cb = LangChainCallback(run_id="r")

    class Action:
        tool = "send_email"
        tool_input = {"to": "x@y.com", "body": "ssn 123-45-6789"}

    class Gen:
        text = "Final summary for the user."

    class LLMResult:
        generations = [[Gen()]]

    cb.on_agent_action(Action())
    cb.on_llm_end(LLMResult())
    channels = {e.channel_value for e in cb.trace.events}
    assert "inter_agent_message" in channels
    assert cb.trace.events[-1].channel_value == "final_output"
    result = cb.analyze()
    assert any(f.data_type == "ssn" for f in result.findings)


def test_langchain_llm_end_falls_back_to_str():
    cb = LangChainCallback(run_id="r")
    cb.on_llm_end("plain string response")
    assert cb.trace.events[-1].searchable_text == "plain string response"


def test_langgraph_trace_from_state():
    state = {"messages": [
        {"role": "agent", "content": "lookup customer with email a@b.com"},
        {"role": "assistant", "content": "Here is your summary."},
    ]}
    trace = trace_from_state(state, run_id="r")
    assert trace.events[-1].channel_value == "final_output"
    assert trace.events[0].channel_value == "inter_agent_message"


def test_autogen_trace_from_messages():
    trace = trace_from_messages([
        {"name": "researcher", "content": "client ssn is 123-45-6789"},
        {"name": "writer", "content": "Summary complete."},
    ], run_id="r")
    result = AgentLeakRunner().analyze(trace)
    assert trace.events[-1].channel_value == "final_output"
    assert any(f.data_type == "ssn" for f in result.findings)


def test_crewai_callback():
    cb = CrewAICallback(run_id="r")

    class Step:
        tool = "crm"
        tool_input = {"email": "a@b.com"}
        text = "using crm"

    class TaskOut:
        raw = "Final answer to the user."
        agent = "writer"

    cb.step_callback(Step())
    cb.task_callback(TaskOut())
    result = cb.analyze()
    assert any(f.channel == "tool_call" for f in result.findings)
    assert cb.trace.events[-1].channel_value == "final_output"
