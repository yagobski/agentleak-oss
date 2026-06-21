"""Live agent execution — run a real agent against a scenario, capture its trace.

This is the bridge between a *scenario* (a task + private data) and a *trace*
(what an agent actually did). Two execution backends:

- **live** — a real LLM agent (any OpenAI-compatible endpoint: OpenAI,
  OpenRouter, Ollama, vLLM, …) is given the task plus tools, and we record every
  channel it touches. Whether it leaks is up to the model — the result is a real
  audit, not a simulation.
- **scripted** — a deterministic, offline stand-in (no API key) that fetches the
  records and discloses a subset. Useful for demos, CI, and tests.

The LLM is **optional and never imported by the core** — it is only reached when
a user explicitly runs a project's agent. AgentLeak's analysis stays local and
LLM-free.
"""

from __future__ import annotations

from .context import RunContext, build_run_context
from .llm import LLMConfig, LLMError, OpenAICompatLLM, resolve_api_key
from .runner import AgentRunError, run_scenario

__all__ = [
    "RunContext",
    "build_run_context",
    "LLMConfig",
    "LLMError",
    "OpenAICompatLLM",
    "resolve_api_key",
    "AgentRunError",
    "run_scenario",
]
