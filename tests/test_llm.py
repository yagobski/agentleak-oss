"""OpenAI-compatible LLM client — request building and error handling (mocked)."""

from __future__ import annotations

import io
import json
import urllib.error

import pytest

from agentleak.agent.llm import LLMConfig, LLMError, OpenAICompatLLM, resolve_api_key


class _Resp:
    def __init__(self, payload: dict) -> None:
        self._b = json.dumps(payload).encode()

    def read(self) -> bytes:
        return self._b

    def __enter__(self) -> _Resp:
        return self

    def __exit__(self, *a: object) -> bool:
        return False


def _patch(monkeypatch, handler) -> None:
    monkeypatch.setattr("agentleak.agent.llm.urllib.request.urlopen", handler)


def test_chat_builds_request_and_returns_message(monkeypatch):
    seen: dict = {}

    def fake(req, timeout=None):
        seen["url"] = req.full_url
        seen["auth"] = req.get_header("Authorization")
        seen["body"] = json.loads(req.data.decode())
        return _Resp({"choices": [{"message": {"role": "assistant", "content": "hi"}}]})

    _patch(monkeypatch, fake)
    llm = OpenAICompatLLM(LLMConfig(base_url="https://api.openai.com/v1", model="gpt-x", api_key="k"))
    msg = llm.chat([{"role": "user", "content": "x"}], [{"type": "function"}])

    assert msg["content"] == "hi"
    assert seen["url"] == "https://api.openai.com/v1/chat/completions"
    assert seen["auth"] == "Bearer k"
    assert seen["body"]["model"] == "gpt-x"
    assert seen["body"]["tool_choice"] == "auto"


def test_chat_parses_tool_calls(monkeypatch):
    _patch(monkeypatch, lambda req, timeout=None: _Resp(
        {"choices": [{"message": {"role": "assistant", "tool_calls": [
            {"id": "c1", "function": {"name": "get_records", "arguments": "{}"}}]}}]}
    ))
    llm = OpenAICompatLLM(LLMConfig(model="m", api_key="k"))
    msg = llm.chat([], [])
    assert msg["tool_calls"][0]["function"]["name"] == "get_records"


def test_chat_http_error_surfaces_detail(monkeypatch):
    def fake(req, timeout=None):
        raise urllib.error.HTTPError(req.full_url, 401, "Unauthorized", {}, io.BytesIO(b'{"error":"bad key"}'))

    _patch(monkeypatch, fake)
    llm = OpenAICompatLLM(LLMConfig(model="m", api_key="k"))
    with pytest.raises(LLMError, match="401"):
        llm.chat([], [])


def test_chat_url_error_is_friendly(monkeypatch):
    def fake(req, timeout=None):
        raise urllib.error.URLError("connection refused")

    _patch(monkeypatch, fake)
    llm = OpenAICompatLLM(LLMConfig(base_url="http://localhost:11434/v1", model="m"))
    with pytest.raises(LLMError, match="reach LLM endpoint"):
        llm.chat([], [])


def test_chat_no_choices_raises(monkeypatch):
    _patch(monkeypatch, lambda req, timeout=None: _Resp({"choices": []}))
    llm = OpenAICompatLLM(LLMConfig(model="m"))
    with pytest.raises(LLMError, match="no choices"):
        llm.chat([], [])


def test_no_auth_header_without_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    seen: dict = {}

    def fake(req, timeout=None):
        seen["auth"] = req.get_header("Authorization")
        return _Resp({"choices": [{"message": {"content": "ok"}}]})

    _patch(monkeypatch, fake)
    llm = OpenAICompatLLM(LLMConfig(base_url="http://localhost:11434/v1", model="llama", api_key=""))
    llm.chat([], [])
    assert seen["auth"] is None


def test_resolve_api_key_by_host(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "or")
    monkeypatch.setenv("OPENAI_API_KEY", "oa")
    assert resolve_api_key("https://openrouter.ai/api/v1") == "or"
    assert resolve_api_key("https://api.openai.com/v1") == "oa"
    assert resolve_api_key("https://api.openai.com/v1", "explicit") == "explicit"
