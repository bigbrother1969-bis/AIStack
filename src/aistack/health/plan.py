"""
The action plan (asked by the owner, 2026-10-08: "il faudrait que le
cartouche « action requise » soit cliquable et dirige vers une page qui
guide et assiste l'utilisateur sur les actions à réaliser pour réduire
la dette. Idem pour le cartouche « à surveiller » sur le score de
santé").

What to do first, ranked by what it gains — computed from the same
cockpit, weights and quarantine the two scores are computed from, never
estimated apart from them:

- **health**: per domain carrying findings, the points the health score
  gains once the domain is cleared (`OPS-0008`'s formula run again
  without that domain's findings), and what clearing one finding alone
  gains — often nothing while a domain saturates its own penalty, which
  the page says rather than hides;
- **debt**: per group carrying technical debt — a domain, or the
  quarantined code (`OPS-0012`) — the points the technical-debt score
  gains once the group is cleared (one weight per group, `OPS-0008`
  § *Technical debt score*). The quarantine clears at its review date,
  not by an action now: it is listed last, as waiting.

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

# The group name the quarantined code takes in the debt plan.
QUARANTINE = "quarantine"


@dataclass(frozen=True)
class HealthAction:
    """One domain to clear: its findings, and what clearing it gains."""

    domain: str
    findings: tuple[RuntimeFinding, ...]
    gain: int
    gain_one: int


@dataclass(frozen=True)
class DebtAction:
    """One group of technical debt — a domain, or `QUARANTINE` — and what
    clearing it gains on the technical-debt score."""

    group: str
    findings: tuple[RuntimeFinding, ...]
    gain: int
    waiting: bool = False


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
    quarantine: tuple[RuntimeFinding, ...] = (),
) -> tuple[DebtAction, ...]:
    """The groups carrying debt, the actionable ones first, the
    quarantine — cleared by its review, not by an action — last."""

    groups: list[tuple[str, tuple[RuntimeFinding, ...]]] = [
        (domain.name, _debt(domain.findings)) for domain in cockpit.domains
    ]
    if quarantine:
        groups.append((QUARANTINE, _debt(quarantine)))

    def value(without: str | None) -> int:
        return compute_technical_debt_score(
            tuple(findings for name, findings in groups if name != without), weight
        ).value

    now = value(None)
    actions = [
        DebtAction(name, findings, value(name) - now, waiting=name == QUARANTINE)
        for name, findings in groups
        if findings
    ]
    return tuple(sorted(actions, key=lambda action: (action.waiting, -action.gain, action.group)))

