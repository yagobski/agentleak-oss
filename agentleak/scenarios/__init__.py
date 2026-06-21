"""Built-in scenarios and helpers to load their bundled example traces."""

from __future__ import annotations

import json
from importlib import resources

from ..core.scenario import Scenario
from ..core.trace import Trace
from . import customer_support, education, finance, healthcare, hr

_ALL: list[Scenario] = [
    *healthcare.SCENARIOS,
    *finance.SCENARIOS,
    *hr.SCENARIOS,
    *education.SCENARIOS,
    *customer_support.SCENARIOS,
]

SCENARIOS: dict[str, Scenario] = {s.id: s for s in _ALL}


def list_scenarios() -> list[Scenario]:
    return list(_ALL)


def get_scenario(scenario_id: str) -> Scenario:
    try:
        return SCENARIOS[scenario_id]
    except KeyError:
        known = ", ".join(SCENARIOS)
        raise KeyError(f"Unknown scenario '{scenario_id}'. Available: {known}") from None


def load_example_trace(scenario_id: str) -> Trace:
    """Load the packaged example trace for a scenario."""
    scenario = get_scenario(scenario_id)
    if not scenario.example_trace:
        raise ValueError(f"Scenario '{scenario_id}' has no bundled example trace.")
    raw = resources.files("agentleak.examples").joinpath(
        scenario.example_trace
    ).read_text(encoding="utf-8")
    return Trace.from_dict(json.loads(raw))


__all__ = ["SCENARIOS", "list_scenarios", "get_scenario", "load_example_trace", "Scenario"]
