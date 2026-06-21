"""Local web GUI for AgentLeak (optional, requires the ``[gui]`` extra)."""

from __future__ import annotations

from .app import create_app, run_server

__all__ = ["create_app", "run_server"]
