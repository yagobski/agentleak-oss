"""Detector behavior and precision tests."""

from __future__ import annotations

from agentleak.core.detector import Severity, redact
from agentleak.detectors import build_detectors
from agentleak.detectors.custom import CustomDetector, CustomRule
from agentleak.detectors.finance import FinanceDetector
from agentleak.detectors.healthcare import HealthcareDetector
from agentleak.detectors.hr import HRDetector
from agentleak.detectors.pii import PIIDetector
from agentleak.detectors.secrets import SecretsDetector


def _types(detector, text):
    return {m.data_type for m in detector.detect(text)}


# -- PII ----------------------------------------------------------------
def test_pii_detects_email_and_ssn():
    d = PIIDetector()
    types = _types(d, "Contact jane.doe@example.com, SSN 123-45-6789.")
    assert "email" in types
    assert "ssn" in types


def test_pii_credit_card_requires_luhn():
    d = PIIDetector()
    # Valid Visa test number (passes Luhn).
    assert "credit_card" in _types(d, "card 4111 1111 1111 1111")
    # 16 digits that fail Luhn should not be reported as a card.
    assert "credit_card" not in _types(d, "ref 1234 5678 9012 3456 7")


def test_pii_name_requires_keyword_anchor():
    d = PIIDetector()
    assert "person_name" in _types(d, "patient Jean Tremblay arrived")
    # No keyword -> no name match (avoids flagging arbitrary capitalized words).
    assert "person_name" not in _types(d, "New York Times reported today")


def test_pii_clean_text_has_no_findings():
    d = PIIDetector()
    assert d.detect("The patient requires a routine follow-up appointment.") == []


def test_pii_dob_only_with_keyword():
    d = PIIDetector()
    assert "date_of_birth" in _types(d, "DOB 1979-03-12")
    # A bare ISO date (e.g. a timestamp) is not flagged as DOB.
    assert "date_of_birth" not in _types(d, "event at 2026-06-19")


# -- Secrets ------------------------------------------------------------
def test_secrets_detects_aws_and_private_key():
    d = SecretsDetector()
    types = _types(d, "AKIAIOSFODNN7EXAMPLE and -----BEGIN RSA PRIVATE KEY-----")
    assert "aws_access_key" in types
    assert "private_key" in types


def test_secrets_are_critical():
    d = SecretsDetector()
    matches = d.detect("token ghp_" + "a" * 36)
    assert matches
    assert all(m.severity is Severity.CRITICAL for m in matches if m.data_type == "github_token")


def test_secrets_password_assignment():
    d = SecretsDetector()
    assert "secret_assignment" in _types(d, 'password: "hunter2real"')
    # Obvious placeholders are skipped.
    assert "secret_assignment" not in _types(d, "password: redacted")


# -- Healthcare ---------------------------------------------------------
def test_healthcare_nam_is_critical():
    d = HealthcareDetector()
    matches = [m for m in d.detect("NAM TREM12345678") if m.data_type == "health_identifier"]
    assert matches and matches[0].severity is Severity.CRITICAL


def test_healthcare_conditions_and_meds():
    d = HealthcareDetector()
    types = _types(d, "patient has Type 2 diabetes, prescribed insulin")
    assert "health_condition" in types
    assert "medication" in types


# -- Finance ------------------------------------------------------------
def test_finance_account_and_internal_note():
    d = FinanceDetector()
    types = _types(d, "account number 99887766. Internal risk note: prior default.")
    assert "account_number" in types
    assert "internal_note" in types


def test_finance_credit_score_from_flattened_key():
    d = FinanceDetector()
    # Mirrors what content_to_text produces for {"credit_score": 712}.
    assert "credit_score" in _types(d, "credit score: 712")


# -- HR -----------------------------------------------------------------
def test_hr_salary_and_disciplinary():
    d = HRDetector()
    types = _types(d, "salary: 95000; disciplinary action: final warning for misconduct")
    assert "salary" in types
    assert "disciplinary_action" in types


# -- Custom -------------------------------------------------------------
def test_custom_detector_from_config():
    d = CustomDetector.from_config([
        {"name": "project_code", "pattern": r"PROJECT-[A-Z]{3}-[0-9]{4}",
         "severity": "high", "data_type": "internal_project"},
    ])
    matches = d.detect("see PROJECT-ABC-1234 for details")
    assert len(matches) == 1
    assert matches[0].data_type == "internal_project"
    assert matches[0].severity is Severity.HIGH
    assert matches[0].detector == "custom:project_code"


def test_custom_rule_invalid_regex_raises():
    import pytest
    with pytest.raises(ValueError):
        CustomDetector([CustomRule(name="bad", pattern="(")])


# -- Registry -----------------------------------------------------------
def test_build_detectors_respects_toggles():
    detectors = build_detectors({"pii": True, "secrets": False, "healthcare": False,
                                 "finance": False, "hr": False}, None)
    names = {d.name for d in detectors}
    assert names == {"pii_detector"}


def test_build_detectors_none_enables_all_builtins():
    detectors = build_detectors(None, None)
    assert len(detectors) == 5


# -- Redaction ----------------------------------------------------------
def test_redact_keeps_edges():
    assert redact("TREM12345678") == "TR********78"


def test_redact_short_value_fully_masked():
    assert redact("abcd") == "****"
    assert redact("ab") == "**"
