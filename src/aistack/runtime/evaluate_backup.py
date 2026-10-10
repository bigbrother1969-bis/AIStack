"""
Turn `BackupGap`s (`OPS-0006`: backup missing, stale or unreachable) into
`RuntimeFinding`s.

Always cites two `OPS-0004` qualifications, technical debt and deployment
misconfiguration; energy inefficiency and sustainability anomaly do not
apply to this domain.
"""

from __future__ import annotations

from aistack.contracts.finding_message import FindingMessage, part

from collections.abc import Sequence

from aistack.contracts.backup_gap import MISSING, UNREACHABLE, BackupGap
from aistack.contracts.runtime_finding import CitedReading, RuntimeFinding
from aistack.contracts.undeclared import UNDECLARED

# `OPS-0004` vocabulary; `RuntimeFinding.QUALIFICATIONS` holds the full list.
TECHNICAL_DEBT = "OPS-0004/technical-debt"
DEPLOYMENT_MISCONFIGURATION = "OPS-0004/deployment-misconfiguration"

BACKUP_GAP_QUALIFICATIONS = (TECHNICAL_DEBT, DEPLOYMENT_MISCONFIGURATION)

# The `provider_id` `BackupProvider.provider_id` declares.
BACKUP_PROVIDER = "aistack.provider.backup"

SIGNATURE = "OPS-0004"


def evaluate_backup(gaps: Sequence[BackupGap]) -> tuple[RuntimeFinding, ...]:
    """One `RuntimeFinding` per backup gap."""

    return tuple(
        RuntimeFinding(
            subject=gap.reading.path,
            signature=SIGNATURE,
            interpretation=_interpretation(gap),
            remediation=_remediation(gap),
            message=_message(gap),
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

    if gap.reason == UNREACHABLE:
        return (
            f"{reading.path} could not be read ({reading.unreachable}), so "
            f"whether its backup exists or is fresh is unknown — the "
            f"condition OPS-0004's fourth reference case names (technical "
            f"debt, deployment misconfiguration)."
        )

    # STALE implies `newest_file_mtime` is set; test both so mypy can narrow
    # the type.
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
    if gap.reason == UNREACHABLE:
        return (
            f"Check that the disk holding {gap.reading.path} is mounted on "
            f"the host and visible where AIStack runs — a disk mounted on "
            f"demand is not seen from a container while it is unmounted."
        )

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


def _message(gap: BackupGap) -> FindingMessage:
    """The same two sentences as `_interpretation`/`_remediation`, as catalog keys."""

    reading = gap.reading

    if gap.reason == UNREACHABLE:
        return FindingMessage(
            interpretation=(
                part("findings.backup.unreachable.interpretation", path=reading.path, error=reading.unreachable),
            ),
            remediation=(part("findings.backup.unreachable.remediation", path=reading.path),),
        )

    if gap.reason == MISSING:
        remediation = (part("findings.backup.missing.remediation", path=reading.path),)
    else:
        remediation = (part("findings.backup.stale.remediation", path=reading.path),)

    if gap.reason == MISSING or reading.newest_file_mtime is None:
        return FindingMessage(
            interpretation=(part("findings.backup.missing.interpretation", path=reading.path),),
            remediation=remediation,
        )

    age_hours = (reading.observed_at - reading.newest_file_mtime).total_seconds() / 3600

    return FindingMessage(
        interpretation=(
            part(
                "findings.backup.stale.interpretation",
                path=reading.path,
                age=f"{age_hours:.1f}",
                threshold=f"{gap.max_age_hours:.1f}",
            ),
        ),
        remediation=remediation,
    )
