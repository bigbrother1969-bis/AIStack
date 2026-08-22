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
    subjects. It proposes no remediation.

    `unit` names what `affected` and `total` count. It defaults
    to `artifacts` because every check until 2026-08-22 counted
    artifacts, and the report said so in hardcoded text.

    `contract-debt` counts contracts and modules, and printing
    "20/56 artifacts" for twenty orphan contracts states
    something false about a heritage of 65 artifacts. A report
    that misnames what it counts is not a smaller defect than
    one that miscounts.
    """

    check: str
    severity: IntegritySeverity
    summary: str
    affected: int
    total: int
    subjects: tuple[str, ...] = field(default_factory=tuple)
    unit: str = "artifacts"
