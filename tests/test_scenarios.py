"""Scenario registry and bundled example-trace tests."""

from __future__ import annotations

import pytest

from agentleak import AgentLeakRunner
from agentleak.scenarios import get_scenario, list_scenarios, load_example_trace

EXPECTED_IDS = {
    "healthcare_patient_summary",
    "finance_loan_review",
    "hr_employee_case",
    "education_document_publication",
    "customer_support_crm",
}


def test_five_scenarios_registered():
    ids = {s.id for s in list_scenarios()}
    assert ids == EXPECTED_IDS


def test_get_unknown_scenario_raises():
    with pytest.raises(KeyError):
        get_scenario("does_not_exist")


@pytest.mark.parametrize("scenario_id", sorted(EXPECTED_IDS))
def test_each_example_trace_loads_and_analyzes(scenario_id):
    trace = load_example_trace(scenario_id)
    assert trace.events
    result = AgentLeakRunner().analyze(trace)
    # Every demo trace is intentionally leaky.
    assert result.findings
    # And every demo keeps its final output clean (the product's whole point).
    levels = {cr.channel: cr.level for cr in result.score.channel_risks}
    assert levels.get("final_output", "none") == "none"


def test_scenarios_have_metadata():
    for s in list_scenarios():
        assert s.description
        assert s.sensitive_data
        assert s.expected_behavior
        assert s.example_trace
