"""Compliance framework mapping."""

from __future__ import annotations

from agentleak import AgentLeakRunner, Trace
from agentleak.scenarios import load_example_trace


def _report(trace: Trace) -> dict:
    return AgentLeakRunner().analyze(trace).to_dict()


def test_clean_run_is_compliant():
    trace = Trace(run_id="clean")
    trace.add_event("final_output", "All good, nothing sensitive.")
    c = _report(trace)["compliance"]
    assert c["summary"]["non_compliant"] == 0
    assert all(fw["status"] == "compliant" for fw in c["frameworks"])


def test_health_leak_trips_gdpr_art9():
    c = _report(load_example_trace("healthcare_patient_summary"))["compliance"]
    gdpr = next(f for f in c["frameworks"] if f["id"] == "gdpr")
    art9 = next(ctrl for ctrl in gdpr["controls"] if ctrl["id"] == "gdpr.art9")
    assert art9["status"] == "at_risk"
    assert art9["evidence"]  # the health data types
    assert gdpr["status"] == "non_compliant"


def test_secret_leak_trips_gdpr_art32():
    trace = Trace(run_id="r")
    trace.add_event("log", "aws key AKIAIOSFODNN7EXAMPLE leaked")
    c = _report(trace)["compliance"]
    gdpr = next(f for f in c["frameworks"] if f["id"] == "gdpr")
    art32 = next(ctrl for ctrl in gdpr["controls"] if ctrl["id"] == "gdpr.art32")
    assert art32["status"] == "at_risk"


def test_nist_privacy_measured_is_info():
    c = _report(load_example_trace("finance_loan_review"))["compliance"]
    nist = next(f for f in c["frameworks"] if f["id"] == "nist_ai_rmf")
    measured = next(ctrl for ctrl in nist["controls"] if ctrl["id"] == "nist.measure2.7")
    assert measured["status"] == "info"


def test_all_frameworks_present():
    c = _report(load_example_trace("hr_employee_case"))["compliance"]
    ids = {f["id"] for f in c["frameworks"]}
    assert ids == {"gdpr", "law25", "nist_ai_rmf", "owasp_llm", "eu_ai_act"}
    assert c["summary"]["total"] == 5
