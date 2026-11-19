from __future__ import annotations

from dataclasses import dataclass

# ADR-0028 § 3: a small closed scale. Higher is worse.
INFORMATION = "information"
WATCH = "watch"
FIX = "fix"
URGENT = "urgent"

SEVERITIES = (INFORMATION, WATCH, FIX, URGENT)


@dataclass(frozen=True)
class Finding:
    """
    One thing the assessment found (ADR-0028 § 3).

    `evidence` is plain facts (a port, a name, a count) and never a secret,
    a file's content or a person's data. `unknown` says what the assessment
    could not establish: a finding never claims more than was read.
    """

    key: str
    severity: str
    title: str
    evidence: tuple[str, ...] = ()
    unknown: str = ""

    def __post_init__(self) -> None:
        if self.severity not in SEVERITIES:
            raise ValueError(f"Unknown severity: {self.severity}")

    def as_dict(self) -> dict[str, object]:
        return {
            "key": self.key,
            "severity": self.severity,
            "title": self.title,
            "evidence": list(self.evidence),
            "unknown": self.unknown,
        }


def worst(findings: list[Finding]) -> str | None:
    """The highest severity among `findings`; None when there are none."""

    if not findings:
        return None
    return max((finding.severity for finding in findings), key=SEVERITIES.index)
