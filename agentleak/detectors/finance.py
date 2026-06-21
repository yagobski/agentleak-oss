"""Financial data detector: IBANs, account numbers, credit scores, income,
loan amounts, balances, and internal risk notes.
"""

from __future__ import annotations

import re

from ..core.detector import Detector, RawMatch, Severity

# Tolerant separator: handles flattened "key: value", JSON quotes, and "=".
_SEP = r"[\"'\s:=#-]*"

IBAN_RE = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b")
ACCOUNT_RE = re.compile(
    r"(?i)\b(?:account|acct|compte)(?:\s*(?:number|no|num|#))?" + _SEP + r"([0-9]{6,})"
)
CREDIT_SCORE_RE = re.compile(r"(?i)\bcredit\s*score" + _SEP + r"([0-9]{3})\b")
INCOME_RE = re.compile(
    r"(?i)\b(?:income|revenue|revenu|salary income|gross income)" + _SEP + r"\$?([0-9][0-9,]{3,})"
)
LOAN_RE = re.compile(
    r"(?i)\b(?:loan|mortgage|prêt|pret)(?:\s*(?:amount|montant))?" + _SEP + r"\$?([0-9][0-9,]{3,})"
)
BALANCE_RE = re.compile(r"(?i)\b(?:balance|solde)" + _SEP + r"\$?([0-9][0-9,]{2,})")
INTERNAL_NOTE_RE = re.compile(
    r"(?i)\b(?:internal (?:risk )?note|risk note|underwriter note|internal assessment)\b"
)


class FinanceDetector(Detector):
    name = "finance_detector"

    def detect(self, text: str) -> list[RawMatch]:
        matches: list[RawMatch] = []

        for m in IBAN_RE.finditer(text):
            # Require at least one digit beyond the country/check prefix to
            # avoid matching ordinary uppercase tokens.
            if any(ch.isdigit() for ch in m.group(0)[4:]):
                matches.append(self._match(
                    data_type="iban", severity=Severity.HIGH, confidence=0.75,
                    matched_value=m.group(0),
                    recommendation="Mask IBANs before inter-agent messages and tool calls.",
                ))

        for m in ACCOUNT_RE.finditer(text):
            matches.append(self._match(
                data_type="account_number", severity=Severity.HIGH, confidence=0.8,
                matched_value=m.group(1),
                recommendation="Never forward full account numbers; use last-4 or a token.",
            ))

        for m in CREDIT_SCORE_RE.finditer(text):
            matches.append(self._match(
                data_type="credit_score", severity=Severity.MEDIUM, confidence=0.8,
                matched_value=m.group(1),
                recommendation="Keep credit scores in authorized channels only.",
            ))

        for m in INCOME_RE.finditer(text):
            matches.append(self._match(
                data_type="income", severity=Severity.MEDIUM, confidence=0.7,
                matched_value=m.group(1),
                recommendation="Avoid exposing exact income figures across agents.",
            ))

        for m in LOAN_RE.finditer(text):
            matches.append(self._match(
                data_type="loan_amount", severity=Severity.MEDIUM, confidence=0.65,
                matched_value=m.group(1),
                recommendation="Generalize loan amounts where the precise value is not required.",
            ))

        for m in BALANCE_RE.finditer(text):
            matches.append(self._match(
                data_type="account_balance", severity=Severity.MEDIUM, confidence=0.6,
                matched_value=m.group(1),
                recommendation="Do not log or share raw account balances.",
            ))

        for m in INTERNAL_NOTE_RE.finditer(text):
            matches.append(self._match(
                data_type="internal_note", severity=Severity.HIGH, confidence=0.7,
                matched_value=m.group(0),
                recommendation="Internal risk notes must never reach the final output or the customer.",
            ))

        return matches
