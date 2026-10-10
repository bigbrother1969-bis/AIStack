"""
Turn `StorageShortage`s (`OPS-0005` thresholds crossed) into `RuntimeFinding`s
qualified as deployment misconfiguration.
"""

from __future__ import annotations

from aistack.contracts.finding_message import FindingMessage, part

from collections.abc import Sequence

from aistack.contracts.runtime_finding import CitedReading, RuntimeFinding
from aistack.contracts.storage_shortage import StorageShortage
from aistack.contracts.storage_threshold import FREE_BYTES
from aistack.contracts.undeclared import UNDECLARED

# `OPS-0004` vocabulary; `RuntimeFinding.QUALIFICATIONS` holds the full list.
DEPLOYMENT_MISCONFIGURATION = "OPS-0004/deployment-misconfiguration"

# The `provider_id` `StorageProvider.provider_id` declares.
STORAGE_PROVIDER = "aistack.provider.storage"

SIGNATURE = "OPS-0004"

_BYTES_PER_GB = 1024**3


def evaluate_storage(
    shortages: Sequence[StorageShortage],
) -> tuple[RuntimeFinding, ...]:
    """One `RuntimeFinding` per short volume."""

    return tuple(
        RuntimeFinding(
            subject=shortage.reading.mount,
            signature=SIGNATURE,
            interpretation=_interpretation(shortage),
            remediation=_remediation(shortage),
            message=_message(shortage),
            confidence="Measured",
            grounding=UNDECLARED,
            evidence=(
                CitedReading(
                    provider=STORAGE_PROVIDER,
                    reading=shortage.reading,
                ),
            ),
            qualifications=(DEPLOYMENT_MISCONFIGURATION,),
        )
        for shortage in shortages
    )


def _interpretation(shortage: StorageShortage) -> str:
    reading = shortage.reading

    if shortage.threshold_kind == FREE_BYTES:
        free_gb = reading.free_bytes / _BYTES_PER_GB
        threshold_gb = shortage.threshold_value / _BYTES_PER_GB
        return (
            f"{reading.mount} has {free_gb:.1f} GB free, at or below "
            f"its declared threshold of {threshold_gb:.1f} GB — no "
            f"rotation or size limit stood between this volume and "
            f"running out ({DEPLOYMENT_MISCONFIGURATION})."
        )

    return (
        f"{reading.mount} is {reading.percent_used:.1f}% occupied, at "
        f"or above its declared threshold of "
        f"{shortage.threshold_value:.1f}% — no rotation or size limit "
        f"stood between this volume and running out "
        f"({DEPLOYMENT_MISCONFIGURATION})."
    )


def _remediation(shortage: StorageShortage) -> str:
    return (
        f"Free space on {shortage.reading.mount}, then declare a "
        f"rotation or size cap for whatever grows there unbounded — "
        f"the gap OPS-0004's second reference incident names, not a "
        f"one-time cleanup."
    )


def _message(shortage: StorageShortage) -> FindingMessage:
    """The same two sentences as `_interpretation`/`_remediation`, as catalog keys."""

    reading = shortage.reading
    remediation = (part("findings.storage.remediation", mount=reading.mount),)

    if shortage.threshold_kind == FREE_BYTES:
        return FindingMessage(
            interpretation=(
                part(
                    "findings.storage.free.interpretation",
                    mount=reading.mount,
                    free=f"{reading.free_bytes / _BYTES_PER_GB:.1f}",
                    threshold=f"{shortage.threshold_value / _BYTES_PER_GB:.1f}",
                    qualification=DEPLOYMENT_MISCONFIGURATION,
                ),
            ),
            remediation=remediation,
        )

    return FindingMessage(
        interpretation=(
            part(
                "findings.storage.percent.interpretation",
                mount=reading.mount,
                used=f"{reading.percent_used:.1f}",
                threshold=f"{shortage.threshold_value:.1f}",
                qualification=DEPLOYMENT_MISCONFIGURATION,
            ),
        ),
        remediation=remediation,
    )
