"""
Turn `PraTestGap`s (`OPS-0009` restore tests untested, failed, stale or not
declared) into `RuntimeFinding`s.

Always cites three `OPS-0004` qualifications: technical debt, sustainability
anomaly and deployment misconfiguration. Energy inefficiency does not apply
to this domain.
"""

from __future__ import annotations

from aistack.contracts.finding_message import FindingMessage, part

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

# `OPS-0004` vocabulary; `RuntimeFinding.QUALIFICATIONS` holds the full list.
TECHNICAL_DEBT = "OPS-0004/technical-debt"
SUSTAINABILITY_ANOMALY = "OPS-0004/sustainability-anomaly"
DEPLOYMENT_MISCONFIGURATION = "OPS-0004/deployment-misconfiguration"

PRA_TEST_GAP_QUALIFICATIONS = (
    TECHNICAL_DEBT,
    SUSTAINABILITY_ANOMALY,
    DEPLOYMENT_MISCONFIGURATION,
)

# A reading is loaded from YAML, not collected by a provider, so the loader
# itself is cited as the source.
PRA_TESTS_SOURCE = "aistack.pra.yaml.load_pra_tests_yaml"

SIGNATURE = "OPS-0004"


def evaluate_pra_tests(gaps: Sequence[PraTestGap]) -> tuple[RuntimeFinding, ...]:
    """One `RuntimeFinding` per restore-test gap."""

    return tuple(
        RuntimeFinding(
            subject=gap.reading.service,
            signature=SIGNATURE,
            interpretation=_interpretation(gap),
            remediation=_remediation(gap),
            message=_message(gap),
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

            # STALE implies `tested_at` is set; check it so mypy can narrow
            # the type.
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

    # Only UNTESTED remains after the checks above.
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


def _message(gap: PraTestGap) -> FindingMessage:
    """The same two sentences as `_interpretation`/`_remediation`, as catalog keys."""

    service = gap.reading.service

    if gap.reason == FAILED_REASON:
        return FindingMessage(
            interpretation=(part("findings.pra_tests.failed.interpretation", service=service),),
            remediation=(part("findings.pra_tests.failed.remediation", service=service),),
        )

    if gap.reason == STALE:
        reading = gap.reading
        threshold = f"{gap.max_age_days:.1f}"
        remediation = (part("findings.pra_tests.stale.remediation", service=service),)

        if reading.tested_at is None:
            return FindingMessage(
                interpretation=(
                    part(
                        "findings.pra_tests.stale_unknown_age.interpretation",
                        service=service,
                        threshold=threshold,
                    ),
                ),
                remediation=remediation,
            )

        age_days = (reading.observed_at - reading.tested_at).total_seconds() / 86400

        return FindingMessage(
            interpretation=(
                part(
                    "findings.pra_tests.stale.interpretation",
                    service=service,
                    age=f"{age_days:.1f}",
                    threshold=threshold,
                ),
            ),
            remediation=remediation,
        )

    if gap.reason == NOT_DECLARED:
        return FindingMessage(
            interpretation=(part("findings.pra_tests.not_declared.interpretation", service=service),),
            remediation=(part("findings.pra_tests.not_declared.remediation", service=service),),
        )

    return FindingMessage(
        interpretation=(part("findings.pra_tests.untested.interpretation", service=service),),
        remediation=(part("findings.pra_tests.untested.remediation", service=service),),
    )
