"""Built-in detectors and a registry that assembles the active set from
configuration toggles.
"""

from __future__ import annotations

from ..core.detector import Detector
from .custom import CustomDetector, CustomRule
from .finance import FinanceDetector
from .healthcare import HealthcareDetector
from .hr import HRDetector
from .pii import PIIDetector
from .secrets import SecretsDetector

# Maps the config flag name -> detector class.
BUILTIN_DETECTORS: dict[str, type[Detector]] = {
    "pii": PIIDetector,
    "secrets": SecretsDetector,
    "healthcare": HealthcareDetector,
    "finance": FinanceDetector,
    "hr": HRDetector,
}


def build_detectors(
    toggles: dict[str, bool] | None = None,
    custom_rules: list[dict] | None = None,
) -> list[Detector]:
    """Instantiate the enabled detectors.

    ``toggles`` mirrors the ``detectors:`` block of ``agentleak.yaml``. When it
    is ``None`` (e.g. ad-hoc SDK use) every built-in detector is enabled.
    """
    detectors: list[Detector] = []
    for flag, cls in BUILTIN_DETECTORS.items():
        if toggles is None or toggles.get(flag, False):
            detectors.append(cls())
    custom = CustomDetector.from_config(custom_rules)
    if custom.rules:
        detectors.append(custom)
    return detectors


__all__ = [
    "Detector",
    "PIIDetector",
    "SecretsDetector",
    "HealthcareDetector",
    "FinanceDetector",
    "HRDetector",
    "CustomDetector",
    "CustomRule",
    "BUILTIN_DETECTORS",
    "build_detectors",
]
