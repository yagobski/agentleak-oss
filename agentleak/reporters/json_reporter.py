"""JSON report — the machine-readable, canonical output."""

from __future__ import annotations

import json
from typing import Any

from ..core.report import AnalysisResult


def render(result: AnalysisResult) -> str:
    return json.dumps(result.to_dict(), indent=2, ensure_ascii=False)


def render_dict(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False)
