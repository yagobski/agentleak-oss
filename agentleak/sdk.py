"""Lightweight Python SDK: a ``capture()`` context manager and a ``@monitor``
decorator for recording function calls into a trace without wiring a full
framework integration.

Example::

    from agentleak import capture, monitor

    @monitor(channel="tool_call")
    def call_crm(customer_id):
        return {"customer_email": "test@example.com", "account_id": "ACC-12345"}

    with capture(run_id="demo") as cap:
        call_crm(42)

    result = cap.analyze()
    print(result.privacy_score, result.verdict)
"""

from __future__ import annotations

import functools
import threading
from collections.abc import Callable
from typing import Any, TypeVar

from .core.config import Config
from .core.report import AnalysisResult
from .core.runner import AgentLeakRunner
from .core.trace import Channel, Trace

_local = threading.local()
F = TypeVar("F", bound=Callable[..., Any])


class Capture:
    """An active recording session backed by a :class:`Trace`."""

    def __init__(
        self,
        run_id: str = "run",
        agent_name: str = "agent",
        config: Config | None = None,
    ) -> None:
        self.trace = Trace(run_id=run_id, agent_name=agent_name)
        self.config = config
        self._token: Capture | None = None

    def __enter__(self) -> Capture:
        self._token = getattr(_local, "active", None)
        _local.active = self
        return self

    def __exit__(self, *exc: object) -> None:
        _local.active = self._token

    def analyze(self) -> AnalysisResult:
        return AgentLeakRunner(self.config).analyze(self.trace)


def capture(
    run_id: str = "run",
    agent_name: str = "agent",
    config: Config | None = None,
) -> Capture:
    """Start a capture session (use as a ``with`` block)."""
    return Capture(run_id=run_id, agent_name=agent_name, config=config)


def active_capture() -> Capture | None:
    return getattr(_local, "active", None)


def record(
    channel: str | Channel,
    content: Any,
    *,
    source: str = "sdk",
    target: str = "unknown",
    metadata: dict[str, Any] | None = None,
) -> None:
    """Manually record an event into the active capture, if any."""
    cap = active_capture()
    if cap is not None:
        cap.trace.add_event(
            channel=channel, content=content, source=source, target=target,
            metadata=metadata or {},
        )


def monitor(
    channel: str | Channel = "tool_call",
    *,
    capture_args: bool = True,
    capture_result: bool = True,
    source: str | None = None,
    target: str = "tool",
) -> Callable[[F], F]:
    """Decorator that records each call of the wrapped function as an event.

    Only records while a :func:`capture` session is active, so decorating
    production functions is safe and a no-op outside of tests.
    """

    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            result = fn(*args, **kwargs)
            cap = active_capture()
            if cap is not None:
                payload: dict[str, Any] = {"function": fn.__name__}
                if capture_args:
                    if args:
                        payload["args"] = list(args)
                    if kwargs:
                        payload["kwargs"] = dict(kwargs)
                if capture_result:
                    payload["result"] = result
                cap.trace.add_event(
                    channel=channel,
                    content=payload,
                    source=source or fn.__name__,
                    target=target,
                    metadata={"function": fn.__qualname__},
                )
            return result

        return wrapper  # type: ignore[return-value]

    return decorator


__all__ = ["Capture", "capture", "active_capture", "record", "monitor"]
