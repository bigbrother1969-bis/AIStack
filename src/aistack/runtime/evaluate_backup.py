"""
`evaluate_backup` — the Sauvegarde/PRA analogue of `evaluate_storage`
and `evaluate_services`, correlating an already-confirmed `BackupGap`
into a `RuntimeFinding` citing the two `OPS-0004` qualifications the
owner confirmed for this domain's fourth reference case: the owner's
own stated requirement to verify that a backup actually exists, is
functional, and is not too old (`OPS-0004` § *Fourth reference case*,
`PLAN-J7`, `claude/PLAN-J7-HEALTH-COCKPIT-2026-09-11.md`).

**Not an incident — a declared requirement, examined the same way.**
Unlike the second and third reference incidents, this case is not a
past outage the owner described after the fact; it is a standing
requirement the owner stated directly, examined once against
`OPS-0004`'s full closed vocabulary the same way an incident would be
(`GOV-P-001`: the owner states the knowledge, this module invents
nothing beyond it). The distinction is recorded here, and in
`OPS-0004` itself, rather than folded silently into "incident"
language that would overstate what actually happened.

**A separate function, not a branch inside `evaluate`.** Same
reasoning `evaluate_storage`/`evaluate_services` already give: a
`BackupGap` has no second reading to correlate against — a backup
location's own existence and freshness, read once, already say
whether it qualifies (`find_backup_gaps`, against `OPS-0006`).

**Qualifications are fixed, not derived per finding.** Mirrors
`evaluate_services`: always cites two — technical debt, deployment
misconfiguration — because that is what the owner confirmed for this
case's full vocabulary examination, not something re-derived per
gap. Energy inefficiency and sustainability anomaly were explicitly
excluded by the owner and are never cited here.
"""

from __future__ import annotations

from collections.abc import Sequence

from aistack.contracts.backup_gap import MISSING, BackupGap
from aistack.contracts.runtime_finding import CitedReading, RuntimeFinding
from aistack.contracts.undeclared import UNDECLARED

# `OPS-0004`'s own vocabulary — see `RuntimeFinding.QUALIFICATIONS` for
# the full closed list.
TECHNICAL_DEBT = "OPS-0004/technical-debt"
DEPLOYMENT_MISCONFIGURATION = "OPS-0004/deployment-misconfiguration"

# The two qualifications the owner confirmed for the fourth reference
# case — energy inefficiency and sustainability anomaly were examined
# and explicitly excluded.
BACKUP_GAP_QUALIFICATIONS = (TECHNICAL_DEBT, DEPLOYMENT_MISCONFIGURATION)

# The `provider_id` `BackupProvider.provider_id` declares.
BACKUP_PROVIDER = "aistack.provider.backup"

# The signature `RuntimeFinding.signature` cites — `OPS-0004` itself,
# the register that authors this correlation, the same role it plays
# for `evaluate_storage`/`evaluate_services`.
SIGNATURE = "OPS-0004"


def evaluate_backup(gaps: Sequence[BackupGap]) -> tuple[RuntimeFinding, ...]:
    """
    One `RuntimeFinding` per backup location `find_backup_gaps`
    already found failing, citing the two qualifications the owner
    confirmed for `OPS-0004`'s fourth reference case.

    Pure: gaps already found in, findings out — the same discipline
    `evaluate_storage`/`evaluate_services` already hold.
    """

    return tuple(
        RuntimeFinding(
            subject=gap.reading.path,
            signature=SIGNATURE,
            interpretation=_interpretation(gap),
            remediation=_remediation(gap),
            confidence="Measured",
            grounding=UNDECLARED,
            evidence=(
                CitedReading(provider=BACKUP_PROVIDER, reading=gap.reading),
            ),
            qualifications=BACKUP_GAP_QUALIFICATIONS,
        )
        for gap in gaps
    )


def _interpretation(gap: BackupGap) -> str:
    reading = gap.reading

    # `BackupGap.__post_init__` already guarantees `reason == STALE`
    # implies `newest_file_mtime is not None` — but that guarantee
    # lives on a different type, so mypy cannot see it from here.
    # Checking both conditions together, rather than asserting past
    # the second one, narrows `newest_file_mtime` for the rest of this
    # function without a bare `assert`.
    if gap.reason == MISSING or reading.newest_file_mtime is None:
        return (
            f"{reading.path} holds no backup file at all — the condition "
            f"OPS-0004's fourth reference case names (technical debt, "
            f"deployment misconfiguration)."
        )

    age_hours = (
        reading.observed_at - reading.newest_file_mtime
    ).total_seconds() / 3600

    return (
        f"{reading.path}'s newest backup is {age_hours:.1f} hours old, "
        f"above its declared threshold of {gap.max_age_hours:.1f} hours "
        f"— the condition OPS-0004's fourth reference case names "
        f"(technical debt, deployment misconfiguration)."
    )


def _remediation(gap: BackupGap) -> str:
    if gap.reason == MISSING:
        return (
            f"Verify the backup job that should write to "
            f"{gap.reading.path} is actually running, and correct why "
            f"it has not produced a file — the gap OPS-0004's fourth "
            f"reference case names, not a one-time manual backup."
        )

    return (
        f"Investigate why {gap.reading.path}'s backup job has not run "
        f"recently and restore its schedule — the gap OPS-0004's fourth "
        f"reference case names, not a one-time manual backup."
    )
