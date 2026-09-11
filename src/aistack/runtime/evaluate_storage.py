"""
`evaluate_storage` — the storage-capacity analogue of `evaluate`
(`aistack.runtime.evaluate`), correlating an already-confirmed
`StorageShortage` into a `RuntimeFinding` citing `OPS-0004`'s
`deployment misconfiguration` — the qualification GIGABYTE's disk
exhaustion named (`OPS-0004` § *Second reference incident*, `PLAN-J7`,
`claude/PLAN-J7-HEALTH-COCKPIT-2026-09-11.md`).

**A separate function, not a branch inside `evaluate`.** `evaluate`
pairs `UnexplainedConsumption` against `TemperatureReading` for
`energy inefficiency`/`sustainability anomaly` — two readings
corroborating each other. A `StorageShortage` has no second reading to
correlate against: a volume's own occupancy is either short or it is
not, decided already by `find_storage_shortage` against `OPS-0005`.
Folding this in would quietly widen what `evaluate`'s own docstring
documents as its scope ("two of OPS-0004's four qualifications,
deliberately") rather than keep that account accurate.

**Not wired into `aistack.kernel.evidence.Evidence`.** That alias
still names only `ContainerCpuReading | TemperatureReading`
(`aistack/kernel/evidence/evidence.py`) because nothing in the Kernel
Runtime's collection pipeline touches storage yet — the same reason
`evaluate` itself is a plain function outside that machinery, per its
own docstring. `CitedReading.reading` is widened to accept
`StorageReading` (`aistack.contracts.runtime_finding`) because a
finding this module builds cites one directly; the kernel-level
alias is a separate, larger claim this change does not make.
"""

from __future__ import annotations

from collections.abc import Sequence

from aistack.contracts.runtime_finding import CitedReading, RuntimeFinding
from aistack.contracts.storage_shortage import StorageShortage
from aistack.contracts.storage_threshold import FREE_BYTES
from aistack.contracts.undeclared import UNDECLARED

# `OPS-0004`'s own vocabulary — see `RuntimeFinding.QUALIFICATIONS`
# for the full closed list.
DEPLOYMENT_MISCONFIGURATION = "OPS-0004/deployment-misconfiguration"

# The `provider_id` `StorageProvider.provider_id` declares.
STORAGE_PROVIDER = "aistack.provider.storage"

# The signature `RuntimeFinding.signature` cites — `OPS-0004` itself,
# the register that authors this correlation, the same role it plays
# for `evaluate`.
SIGNATURE = "OPS-0004"

_BYTES_PER_GB = 1024**3


def evaluate_storage(
    shortages: Sequence[StorageShortage],
) -> tuple[RuntimeFinding, ...]:
    """
    One `RuntimeFinding` per volume `find_storage_shortage` already
    found short, citing `deployment misconfiguration`.

    Pure: shortages already found in, findings out — the same
    discipline `evaluate` holds.
    """

    return tuple(
        RuntimeFinding(
            subject=shortage.reading.mount,
            signature=SIGNATURE,
            interpretation=_interpretation(shortage),
            remediation=_remediation(shortage),
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
