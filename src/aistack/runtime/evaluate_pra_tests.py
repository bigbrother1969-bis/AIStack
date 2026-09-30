"""
`evaluate_pra_tests` — the Tests-PRA-domain analogue of
`evaluate_backup`, correlating an already-confirmed `PraTestGap` into
a `RuntimeFinding` citing the three `OPS-0004` qualifications the
owner confirmed when `PLAN-J11` § 11.9.1's third and last named gap
("tests PRA") was reopened, 2026-09-23
(`claude/PLAN-J11-CONSOLE-2026-09-11.md`).

**A reopened, declared requirement, examined the same way the fourth
reference case was.** `OPS-0006` (2026-09-11) named periodic restore
tests out of scope for Sauvegarde/PRA v1; the owner reopened exactly
that boundary, on her own explicit decision, once "dette technique"
and "CMDB temps réel" — the other two `PLAN-J11` § 11.9.1 gaps — were
closed the same day. `GOV-P-001` applies the same way it did for the
fourth reference case: the owner states the requirement and the
qualifications examined against it, this module invents nothing
beyond what she confirmed.

**A separate function, not a branch inside `evaluate`.** Same
reasoning `evaluate_backup`/`evaluate_services` already give: a
`PraTestGap` has no second reading to correlate against — one
declared service's own last-known test state, read once, already
says whether it qualifies (`find_pra_test_gaps`, against `OPS-0009`).

**Qualifications are fixed, not derived per finding.** Mirrors
`evaluate_services`: always cites three — technical debt,
sustainability anomaly, deployment misconfiguration — because that is
what the owner confirmed for this case's full vocabulary examination
(2026-09-23), not something re-derived per gap. Energy inefficiency
was explicitly excluded by the owner and is never cited here — the
same exclusion `evaluate_services` already makes for its own third
reference incident, for the same case-by-case reason: examined and
found not to apply, not assumed absent by analogy.

**A fourth reason, an eighth reference case, the same three
qualifications.** 1.6 tranche 4 (R9, 2026-09-30) reopened this
domain once more to add `NOT_DECLARED`: a service `OPS-0010` already
declares stateful but `OPS-0009`'s own file never names at all. Cadred
separately (2026-09-30) rather than assumed by analogy with the first
three reasons — the owner confirmed the same three qualifications
apply, energy inefficiency staying excluded here too.
"""

from __future__ import annotations

from collections.abc import Sequence

from aistack.contracts.pra_test_gap import (
    FAILED_REASON,
    NOT_DECLARED,
    STALE,
    UNTESTED,
    PraTestGap,
)
from aistack.contracts.runtime_finding import CitedReading, RuntimeFinding
from aistack.contracts.undeclared import UNDECLARED

# `OPS-0004`'s own vocabulary — see `RuntimeFinding.QUALIFICATIONS` for
# the full closed list.
TECHNICAL_DEBT = "OPS-0004/technical-debt"
SUSTAINABILITY_ANOMALY = "OPS-0004/sustainability-anomaly"
DEPLOYMENT_MISCONFIGURATION = "OPS-0004/deployment-misconfiguration"

# The three qualifications the owner confirmed when this gap was
# reopened, 2026-09-23 — energy inefficiency was examined and
# explicitly excluded.
PRA_TEST_GAP_QUALIFICATIONS = (
    TECHNICAL_DEBT,
    SUSTAINABILITY_ANOMALY,
    DEPLOYMENT_MISCONFIGURATION,
)

# There is no provider behind a `PraTestReading` — it is loaded
# directly from `OPS-0009`'s declared YAML
# (`aistack.pra.yaml.load_pra_tests_yaml`), not collected from a live
# system. `CitedReading.provider` still names something, the same way
# every other citation in this heritage does; this names the loader
# itself, the closest analogue to a `provider_id` a declared-only
# record has.
PRA_TESTS_SOURCE = "aistack.pra.yaml.load_pra_tests_yaml"

# The signature `RuntimeFinding.signature` cites — `OPS-0004` itself,
# the register that authors this correlation, the same role it plays
# for `evaluate_backup`/`evaluate_services`.
SIGNATURE = "OPS-0004"


def evaluate_pra_tests(gaps: Sequence[PraTestGap]) -> tuple[RuntimeFinding, ...]:
    """
    One `RuntimeFinding` per declared service `find_pra_test_gaps`
    already found failing, citing the three qualifications the owner
    confirmed when this gap was reopened.

    Pure: gaps already found in, findings out — the same discipline
    `evaluate_backup`/`evaluate_services` already hold.
    """

    return tuple(
        RuntimeFinding(
            subject=gap.reading.service,
            signature=SIGNATURE,
            interpretation=_interpretation(gap),
            remediation=_remediation(gap),
            confidence="Measured",
            grounding=UNDECLARED,
            evidence=(
                CitedReading(provider=PRA_TESTS_SOURCE, reading=gap.reading),
            ),
            qualifications=PRA_TEST_GAP_QUALIFICATIONS,
        )
        for gap in gaps
    )


def _interpretation(gap: PraTestGap) -> str:
    service = gap.reading.service

    if gap.reason == FAILED_REASON:
        return (
            f"{service}'s last recorded restore test failed — the "
            f"condition OPS-0009's restore-test freshness gap names "
            f"(technical debt, sustainability anomaly, deployment "
            f"misconfiguration)."
        )

    if gap.reason == STALE:
        reading = gap.reading

        # `PraTestGap.__post_init__` already guarantees `reason ==
        # STALE` implies `tested_at is not None` — but that guarantee
        # lives on a different type, so mypy cannot see it from here.
        # Checking it directly, rather than asserting past it, narrows
        # it for the rest of this branch without a bare `assert`.
        if reading.tested_at is None:
            return (
                f"{service}'s last successful restore test is older than "
                f"its declared threshold of {gap.max_age_days:.1f} days — "
                f"the condition OPS-0009's restore-test freshness gap "
                f"names (technical debt, sustainability anomaly, "
                f"deployment misconfiguration)."
            )

        age_days = (
            reading.observed_at - reading.tested_at
        ).total_seconds() / 86400

        return (
            f"{service}'s last successful restore test is {age_days:.1f} "
            f"days old, above its declared threshold of "
            f"{gap.max_age_days:.1f} days — the condition OPS-0009's "
            f"restore-test freshness gap names (technical debt, "
            f"sustainability anomaly, deployment misconfiguration)."
        )

    if gap.reason == NOT_DECLARED:
        return (
            f"{service} is declared stateful in OPS-0010's own file but "
            f"names no entry at all in OPS-0009's own file — the "
            f"condition OPS-0004's eighth reference case names "
            f"(technical debt, sustainability anomaly, deployment "
            f"misconfiguration)."
        )

    # `PraTestGap.__post_init__` restricts `reason` to `REASONS`
    # (`FAILED_REASON`/`STALE`/`NOT_DECLARED`/`UNTESTED`); the three
    # above are each checked, so only `UNTESTED` reaches here.
    assert gap.reason == UNTESTED

    return (
        f"{service} has never had a restore test recorded — the "
        f"condition OPS-0009's restore-test freshness gap names "
        f"(technical debt, sustainability anomaly, deployment "
        f"misconfiguration)."
    )


def _remediation(gap: PraTestGap) -> str:
    service = gap.reading.service

    if gap.reason == FAILED_REASON:
        return (
            f"Investigate why {service}'s restore failed and correct what "
            f"blocked it, then record a new attempt in OPS-0009's own "
            f"declared file — the gap this reference case names, not a "
            f"one-time fix."
        )

    if gap.reason == STALE:
        return (
            f"Perform a real restore test for {service} and record its "
            f"outcome in OPS-0009's own declared file — the gap this "
            f"reference case names, not a one-time manual test."
        )

    if gap.reason == NOT_DECLARED:
        return (
            f"Add {service} to OPS-0009's own declared file with "
            f"last_test: null — never a guessed date or status — then "
            f"perform its first real restore test and record the real "
            f"outcome."
        )

    assert gap.reason == UNTESTED

    return (
        f"Perform {service}'s first real restore test and record its "
        f"outcome in OPS-0009's own declared file — the gap this "
        f"reference case names."
    )
