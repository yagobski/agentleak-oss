"""Healthcare data detector: synthetic health identifiers (NAM-like),
diagnoses/conditions, and medications.

Kept intentionally simple (regex + dictionaries) per the V1 spec. The NAM-like
pattern is treated as *critical* because a government health-insurance number
is a direct, regulated re-identifier tied to medical records.

Note: the NAM-like pattern matches a synthetic shape only; it does not claim to
validate real Québec health-insurance numbers.
"""

from __future__ import annotations

import re

from ..core.detector import Detector, RawMatch, Severity

# Synthetic NAM shape: 4 letters + 8 digits (e.g. TREM12345678).
NAM_LIKE_RE = re.compile(r"\b[A-Z]{4}\d{8}\b")
# US-style MRN / medical record number anchored on a keyword.
MRN_RE = re.compile(r"(?i)\b(?:mrn|medical record(?: number)?|health id)\b[:\s#]*([A-Z0-9-]{5,})")

HEALTH_CONDITIONS = [
    "diabetes", "cancer", "hypertension", "asthma", "depression", "anxiety",
    "pregnancy", "hiv", "aids", "hepatitis", "schizophrenia", "bipolar",
    "epilepsy", "alzheimer", "parkinson", "leukemia", "tumor", "stroke",
    "diabète", "cancer du", "hypertension", "asthme", "dépression", "grossesse",
]

MEDICATIONS = [
    "insulin", "metformin", "chemotherapy", "morphine", "oxycodone",
    "antidepressant", "antiretroviral", "lithium", "warfarin", "prednisone",
    "insuline", "chimiothérapie",
]


def _dictionary_regex(terms: list[str]) -> re.Pattern[str]:
    escaped = sorted({re.escape(t) for t in terms}, key=len, reverse=True)
    return re.compile(r"(?i)\b(" + "|".join(escaped) + r")\b")


_CONDITION_RE = _dictionary_regex(HEALTH_CONDITIONS)
_MEDICATION_RE = _dictionary_regex(MEDICATIONS)


class HealthcareDetector(Detector):
    name = "healthcare_detector"

    def detect(self, text: str) -> list[RawMatch]:
        matches: list[RawMatch] = []

        for m in NAM_LIKE_RE.finditer(text):
            matches.append(RawMatch(
                data_type="health_identifier", severity=Severity.CRITICAL, confidence=0.85,
                matched_value=m.group(0), detector="healthcare_nam_detector",
                recommendation="Remove or mask health identifiers before calling external tools.",
            ))

        for m in MRN_RE.finditer(text):
            matches.append(self._match(
                data_type="health_identifier", severity=Severity.CRITICAL, confidence=0.8,
                matched_value=m.group(1),
                recommendation="Remove or mask medical record numbers before internal channels.",
            ))

        for m in _CONDITION_RE.finditer(text):
            matches.append(self._match(
                data_type="health_condition", severity=Severity.MEDIUM, confidence=0.7,
                matched_value=m.group(1),
                recommendation="Avoid restating specific diagnoses in channels that don't need them.",
            ))

        for m in _MEDICATION_RE.finditer(text):
            matches.append(self._match(
                data_type="medication", severity=Severity.MEDIUM, confidence=0.65,
                matched_value=m.group(1),
                recommendation="Medication details reveal conditions; share only with authorized agents.",
            ))

        return matches
