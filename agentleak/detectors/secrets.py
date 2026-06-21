"""Technical secret detector: API keys, tokens, private keys, connection
strings, and password/secret assignments.

Leaked credentials are treated as the most severe class — a leaked key is
immediately actionable by an attacker — so most matches here are critical.
"""

from __future__ import annotations

import re

from ..core.detector import Detector, RawMatch, Severity

AWS_ACCESS_KEY_RE = re.compile(r"\bAKIA[0-9A-Z]{16}\b")
GITHUB_TOKEN_RE = re.compile(r"\bgh[oprsu]_[A-Za-z0-9]{36}\b")
SLACK_TOKEN_RE = re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")
STRIPE_KEY_RE = re.compile(r"\b[sr]k_(?:live|test)_[A-Za-z0-9]{16,}\b")
JWT_RE = re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b")
PRIVATE_KEY_RE = re.compile(
    r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----"
)
CONNECTION_STRING_RE = re.compile(
    r"(?i)\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis|amqps?)://[^\s'\"]+"
)
# Generic ``password: ...`` / ``api_key = ...`` assignments. Broad, so lower
# confidence; the assigned value must be non-trivial.
SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key)\b"
    r"\s*[:=]\s*[\"']?([^\"'\s,}]{6,})"
)


class SecretsDetector(Detector):
    name = "secrets_detector"

    def detect(self, text: str) -> list[RawMatch]:
        matches: list[RawMatch] = []

        for m in PRIVATE_KEY_RE.finditer(text):
            matches.append(self._match(
                data_type="private_key", severity=Severity.CRITICAL, confidence=0.99,
                matched_value=m.group(0),
                recommendation="Rotate the key immediately; private keys must never enter agent channels.",
            ))

        for m in AWS_ACCESS_KEY_RE.finditer(text):
            matches.append(self._match(
                data_type="aws_access_key", severity=Severity.CRITICAL, confidence=0.97,
                matched_value=m.group(0),
                recommendation="Rotate the AWS key and inject credentials at the runtime boundary only.",
            ))

        for m in GITHUB_TOKEN_RE.finditer(text):
            matches.append(self._match(
                data_type="github_token", severity=Severity.CRITICAL, confidence=0.95,
                matched_value=m.group(0),
                recommendation="Revoke the GitHub token; do not pass tokens through prompts or memory.",
            ))

        for m in SLACK_TOKEN_RE.finditer(text):
            matches.append(self._match(
                data_type="slack_token", severity=Severity.CRITICAL, confidence=0.9,
                matched_value=m.group(0),
                recommendation="Revoke the Slack token; keep secrets out of inter-agent messages.",
            ))

        for m in STRIPE_KEY_RE.finditer(text):
            matches.append(self._match(
                data_type="stripe_key", severity=Severity.CRITICAL, confidence=0.95,
                matched_value=m.group(0),
                recommendation="Rotate the Stripe key; never expose payment provider secrets to agents.",
            ))

        for m in JWT_RE.finditer(text):
            matches.append(self._match(
                data_type="jwt", severity=Severity.HIGH, confidence=0.85,
                matched_value=m.group(0),
                recommendation="Do not store or forward raw JWTs; they may carry identity and claims.",
            ))

        for m in CONNECTION_STRING_RE.finditer(text):
            value = m.group(0)
            has_creds = "@" in value and "://" in value and ":" in value.split("://", 1)[1].split("@")[0]
            matches.append(self._match(
                data_type="connection_string",
                severity=Severity.CRITICAL if has_creds else Severity.HIGH,
                confidence=0.9 if has_creds else 0.75,
                matched_value=value,
                recommendation="Strip database/connection strings (and embedded credentials) from traces.",
            ))

        for m in SECRET_ASSIGNMENT_RE.finditer(text):
            value = m.group(2)
            # Skip obvious placeholders to reduce false positives.
            if value.lower() in {"none", "null", "true", "false", "redacted", "xxxxxx", "******"}:
                continue
            matches.append(self._match(
                data_type="secret_assignment", severity=Severity.HIGH, confidence=0.65,
                matched_value=value,
                recommendation="Remove inline secret assignments from agent payloads and logs.",
            ))

        return matches
