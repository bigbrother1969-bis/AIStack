from dataclasses import dataclass


@dataclass(frozen=True)
class EligibilityReport:
    """
    Result of an eligibility evaluation.
    """

    eligible: bool
    reason: str
