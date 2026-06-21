"""Minimal OpenAI-compatible chat client (stdlib only).

Talks to any endpoint that implements ``POST /chat/completions`` with function
calling — OpenAI, OpenRouter, Together, Groq, vLLM, Ollama (``/v1``), etc. Uses
only the standard library so the package adds no dependency; the network call
happens solely when a user runs a live agent.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


class LLMError(RuntimeError):
    """Raised when the LLM endpoint is unreachable or returns an error."""


# Map a base URL to the conventional env var holding its key.
_KEY_ENV_BY_HOST = {
    "openrouter.ai": "OPENROUTER_API_KEY",
    "api.openai.com": "OPENAI_API_KEY",
    "api.groq.com": "GROQ_API_KEY",
    "api.together.xyz": "TOGETHER_API_KEY",
}


def resolve_api_key(base_url: str, explicit: str = "") -> str:
    """Pick the API key: explicit value first, else the conventional env var."""
    if explicit:
        return explicit
    for host, env in _KEY_ENV_BY_HOST.items():
        if host in base_url:
            return os.environ.get(env, "")
    return os.environ.get("OPENAI_API_KEY", "")


@dataclass
class LLMConfig:
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o-mini"
    api_key: str = ""
    temperature: float = 0.2
    timeout: float = 60.0

    def with_resolved_key(self) -> LLMConfig:
        return LLMConfig(
            base_url=self.base_url.rstrip("/"),
            model=self.model,
            api_key=resolve_api_key(self.base_url, self.api_key),
            temperature=self.temperature,
            timeout=self.timeout,
        )


class OpenAICompatLLM:
    """A thin chat-completions wrapper with tool calling."""

    def __init__(self, config: LLMConfig) -> None:
        self.config = config.with_resolved_key()

    @property
    def model(self) -> str:
        return self.config.model

    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> dict[str, Any]:
        """Return the assistant message dict (with optional ``tool_calls``)."""
        body = json.dumps(
            {
                "model": self.config.model,
                "messages": messages,
                "tools": tools,
                "tool_choice": "auto",
                "temperature": self.config.temperature,
            }
        ).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        req = urllib.request.Request(
            f"{self.config.base_url}/chat/completions", data=body, headers=headers, method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=self.config.timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:  # surface the provider's message
            detail = exc.read().decode("utf-8", "replace")[:300]
            raise LLMError(f"LLM endpoint returned HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise LLMError(f"Could not reach LLM endpoint at {self.config.base_url}: {exc.reason}") from exc

        choices = payload.get("choices") or []
        if not choices:
            raise LLMError(f"LLM returned no choices: {str(payload)[:200]}")
        return choices[0].get("message", {}) or {}
