"""HR data detector: salaries, sick leave, performance reviews, disciplinary
actions, and complaints/grievances.
"""

from __future__ import annotations

import re

from ..core.detector import Detector, RawMatch, Severity

# Tolerant separator: handles flattened "key: value", JSON quotes, and "=".
_SEP = r"[\"'\s:=#-]*"

SALARY_RE = re.compile(
    r"(?i)\b(?:salary|salaire|compensation|base pay)" + _SEP + r"\$?([0-9][0-9,]{3,})"
)
SICK_LEAVE_RE = re.compile(r"(?i)\b(?:sick leave|medical leave|congé maladie|stress leave|fmla)\b")
PERFORMANCE_RE = re.compile(
    r"(?i)\b(?:performance review|performance rating|performance plan|pip|évaluation|underperform\w*)\b"
)
DISCIPLINARY_RE = re.compile(
    r"(?i)\b(?:disciplinary|written warning|final warning|misconduct|reprimand|mesure disciplinaire)\b"
)
COMPLAINT_RE = re.compile(r"(?i)\b(?:grievance|harassment complaint|hr complaint|plainte|whistleblow\w*)\b")
TERMINATION_RE = re.compile(r"(?i)\b(?:terminated|termination|laid off|let go|severance)\b")


class HRDetector(Detector):
    name = "hr_detector"

    def detect(self, text: str) -> list[RawMatch]:
        matches: list[RawMatch] = []

        for m in SALARY_RE.finditer(text):
            matches.append(self._match(
                data_type="salary", severity=Severity.HIGH, confidence=0.75,
                matched_value=m.group(1),
                recommendation="Salary data should only reach explicitly authorized agents.",
            ))

        for m in SICK_LEAVE_RE.finditer(text):
            matches.append(self._match(
                data_type="sick_leave", severity=Severity.HIGH, confidence=0.75,
                matched_value=m.group(0),
                recommendation="Health-related leave is sensitive; keep it out of general channels.",
            ))

        for m in PERFORMANCE_RE.finditer(text):
            matches.append(self._match(
                data_type="performance_review", severity=Severity.MEDIUM, confidence=0.7,
                matched_value=m.group(0),
                recommendation="Do not expose performance assessments outside authorized review flows.",
            ))

        for m in DISCIPLINARY_RE.finditer(text):
            matches.append(self._match(
                data_type="disciplinary_action", severity=Severity.HIGH, confidence=0.8,
                matched_value=m.group(0),
                recommendation="Disciplinary records must not appear in shared memory or logs.",
            ))

        for m in COMPLAINT_RE.finditer(text):
            matches.append(self._match(
                data_type="hr_complaint", severity=Severity.MEDIUM, confidence=0.7,
                matched_value=m.group(0),
                recommendation="Protect complainant identity; restrict complaint details to HR agents.",
            ))

        for m in TERMINATION_RE.finditer(text):
            matches.append(self._match(
                data_type="employment_status", severity=Severity.MEDIUM, confidence=0.6,
                matched_value=m.group(0),
                recommendation="Employment-status changes are confidential until officially communicated.",
            ))

        return matches
