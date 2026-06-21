"""Framework integrations.

The generic recorder works everywhere; the framework-specific adapters add
convenient channel mappings. None of them import their target framework at
module import time, so this package is always safe to import.
"""

from __future__ import annotations

from .generic import AgentLeakCallback, TraceRecorder, from_events

__all__ = ["AgentLeakCallback", "TraceRecorder", "from_events"]
