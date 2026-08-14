from dataclasses import dataclass, field
from enum import Enum


class IntegritySeverity(str, Enum):
    """
    How a check declares the weight of what it observes.

    Severity is declared by the check itself, statically.
    It is not inferred by the engine: an engine produces
    evidence, never a judgement.
    """

    BLOCKING = "blocking"
    WARNING = "warning"
    OBSERVATION = "observation"


@dataclass(frozen=True)
class IntegrityFinding:
    """
    One observed fact about the governed heritage.

    A finding states what was observed and on which
    artifacts. It proposes no remediation.
    """

    check: str
    severity: IntegritySeverity
    summary: str
    affected: int
    total: int
    subjects: tuple[str, ...] = field(default_factory=tuple)
