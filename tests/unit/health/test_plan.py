"""The action plan (2026-10-08): what to fix first, ranked by what it gains."""

from __future__ import annotations

from aistack.contracts.health_score import DomainWeight, HealthScoreWeights
from aistack.contracts.runtime_finding import CitedReading, RuntimeFinding
from aistack.contracts.storage_reading import StorageReading
from aistack.health.cockpit import HealthCockpit, HealthDomain
from aistack.health.plan import QUARANTINE, debt_plan, health_plan
from aistack.health.score import compute_health_score

DEBT = "OPS-0004/technical-debt"


def finding(subject: str, debt: bool = True) -> RuntimeFinding:
    return RuntimeFinding(
        subject=subject,
        signature="OPS-0004",
        interpretation="i",
        remediation="r",
        confidence="Measured",
        grounding="unknown",
        evidence=(
            CitedReading(
                provider="test",
                reading=StorageReading(mount="/", total_bytes=100, used_bytes=99, free_bytes=1),
            ),
        ),
        qualifications=(DEBT,) if debt else ("OPS-0004/deployment-misconfiguration",),
    )


WEIGHTS = HealthScoreWeights(
    weights=(
        DomainWeight(domain="Stockage", points=10),
        DomainWeight(domain="Services", points=15),
        DomainWeight(domain="Tests PRA", points=25),
    )
)
COCKPIT = HealthCockpit(
    domains=(
        HealthDomain(name="Stockage", instrumented=True, findings=(finding("/", debt=False),)),
        HealthDomain(name="Services", instrumented=True),
        HealthDomain(
            name="Tests PRA",
            instrumented=True,
            findings=tuple(finding(name) for name in ("gigabyte", "wordpress", "nextcloud", "immich", "aistack")),
        ),
    )
)


def test_domains_come_most_rewarding_first_with_what_clearing_them_gains():
    now = compute_health_score(COCKPIT, WEIGHTS).value
    plan = health_plan(COCKPIT, WEIGHTS)

    assert [action.domain for action in plan] == ["Tests PRA", "Stockage"]
    pra, storage = plan
    # Tests PRA: 5 findings × 25 saturate the domain at 0; cleared it is
    # worth 100 × 25 / 50 = 50 points, one finding alone nothing.
    assert pra.gain == 50 and pra.gain_one == 0
    assert storage.gain == compute_health_score(
        HealthCockpit(domains=(HealthDomain(name="Stockage", instrumented=True), *COCKPIT.domains[1:])), WEIGHTS
    ).value - now


def test_a_clean_or_unmeasured_domain_is_not_an_action():
    cockpit = HealthCockpit(
        domains=(HealthDomain(name="Services", instrumented=True), HealthDomain(name="GPU", instrumented=False, note="no GPU"))
    )
    assert health_plan(cockpit, WEIGHTS) == ()


def test_debt_groups_gain_one_weight_each_and_the_quarantine_waits_last():
    plan = debt_plan(COCKPIT, 15, quarantine=(finding("Q-001"),))

    assert [(action.group, action.gain, action.waiting) for action in plan] == [
        ("Tests PRA", 15, False),
        (QUARANTINE, 15, True),
    ]
    # A finding not qualified technical debt is no debt to clear.
    assert all(action.group != "Stockage" for action in plan)


def test_no_debt_no_debt_action():
    assert debt_plan(HealthCockpit(domains=(HealthDomain(name="Services", instrumented=True),)), 15) == ()
