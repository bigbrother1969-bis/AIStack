from pathlib import Path
from typing import Protocol

from .report import EligibilityReport


class EligibilityPolicy(Protocol):
    """Contract implemented by all eligibility policies."""

    def evaluate(
        self,
        root: Path,
        path: Path,
    ) -> EligibilityReport:
        ...
