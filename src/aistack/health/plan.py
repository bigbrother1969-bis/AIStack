"""
The action plan: what to do first, ranked by what it gains, computed from
the same cockpit and weights as the two scores.

- **health**: for each domain with findings, the health score points
  gained once the domain is cleared, and by clearing one finding alone
  (often nothing while the domain saturates its penalty, which the page
  says);
- **debt**: for each domain with technical debt, the technical-debt score
  points gained once it is cleared.

Pure: same inputs, same plan.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from aistack.contracts.health_score import HealthScoreWeights
from aistack.contracts.runtime_finding import RuntimeFinding
from aistack.contracts.technical_debt_score import TECHNICAL_DEBT_QUALIFICATION
from aistack.health.cockpit import HealthCockpit
from aistack.health.score import compute_health_score
from aistack.health.technical_debt import compute_technical_debt_score

@dataclass(frozen=True)
class HealthAction:
    """One domain to clear: its findings, and what clearing it gains."""

    domain: str
    findings: tuple[RuntimeFinding, ...]
    gain: int
    gain_one: int


@dataclass(frozen=True)
class DebtAction:
    """One domain carrying technical debt, and what clearing it gains on
    the technical-debt score."""

    group: str
    findings: tuple[RuntimeFinding, ...]
    gain: int


def _with(cockpit: HealthCockpit, name: str, findings: tuple[RuntimeFinding, ...]) -> HealthCockpit:
    return HealthCockpit(
        domains=tuple(
            replace(domain, findings=findings) if domain.name == name else domain
            for domain in cockpit.domains
        )
    )


def health_plan(cockpit: HealthCockpit, weights: HealthScoreWeights) -> tuple[HealthAction, ...]:
    """The domains with findings, the most rewarding first."""

    now = compute_health_score(cockpit, weights).value
    actions = []
    for domain in cockpit.domains:
        if not domain.instrumented or not domain.findings:
            continue
        cleared = compute_health_score(_with(cockpit, domain.name, ()), weights).value
        one = compute_health_score(_with(cockpit, domain.name, domain.findings[1:]), weights).value
        actions.append(HealthAction(domain.name, domain.findings, cleared - now, one - now))
    return tuple(sorted(actions, key=lambda action: (-action.gain, -action.gain_one, action.domain)))


def _debt(findings: tuple[RuntimeFinding, ...]) -> tuple[RuntimeFinding, ...]:
    return tuple(finding for finding in findings if TECHNICAL_DEBT_QUALIFICATION in finding.qualifications)


def debt_plan(
    cockpit: HealthCockpit,
    weight: int,
) -> tuple[DebtAction, ...]:
    """The domains carrying debt, the one gaining most first."""

    groups: list[tuple[str, tuple[RuntimeFinding, ...]]] = [
        (domain.name, _debt(domain.findings)) for domain in cockpit.domains
    ]

    def value(without: str | None) -> int:
        return compute_technical_debt_score(
            tuple(findings for name, findings in groups if name != without), weight
        ).value

    now = value(None)
    actions = [
        DebtAction(name, findings, value(name) - now)
        for name, findings in groups
        if findings
    ]
    return tuple(sorted(actions, key=lambda action: (-action.gain, action.group)))

