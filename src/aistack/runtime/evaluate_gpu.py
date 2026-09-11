"""
`evaluate_gpu` — the GPU-domain analogue of `evaluate_storage`/
`evaluate_backup`, correlating an already-confirmed `GpuAnomaly` into a
`RuntimeFinding` citing all four `OPS-0004` qualifications the owner
confirmed for the fifth reference case: the owner's own stated
requirement to verify that services delegating compute to the GPU
actually do, and to monitor the CPU/GPU duo's consumption
(`OPS-0004` § *Fifth reference case*, `PLAN-J7`,
`claude/PLAN-J7-HEALTH-COCKPIT-2026-09-11.md`).

**Not an incident — a declared requirement, examined the same way as
the fourth.** Mirrors `evaluate_backup`'s own distinction: the owner
did not describe a past GPU failure, but stated a standing requirement,
examined once against `OPS-0004`'s full closed vocabulary the same way
an incident would be (`GOV-P-001`).

**A separate function, not a branch inside `evaluate`.** Same reasoning
`evaluate_storage`/`evaluate_backup` already give: a `GpuAnomaly` has no
second reading to correlate against — one GPU reading, checked against
a declared threshold, already says whether it qualifies
(`find_gpu_anomalies`, against `OPS-0007`).

**All four qualifications, fixed rather than derived per finding.**
Unlike every prior domain — each of which the owner found to carry a
strict subset of `OPS-0004`'s vocabulary — the owner examined this
fifth case and found it to carry technical debt, energy inefficiency,
sustainability anomaly, *and* deployment misconfiguration together,
none excluded. This is the first domain-specific evaluator to cite
`energy inefficiency`: `OPS-0004` § *What this register does not do*
had named it, until this case, as the one qualification `evaluate()`
alone (the original CPU/temperature correlation) had ever cited.
"""

from __future__ import annotations

from collections.abc import Sequence

from aistack.contracts.gpu_anomaly import GpuAnomaly
from aistack.contracts.gpu_threshold import (
    MEMORY_PERCENT,
    TEMPERATURE_CELSIUS,
    UTILIZATION_PERCENT,
)
from aistack.contracts.runtime_finding import CitedReading, RuntimeFinding
from aistack.contracts.undeclared import UNDECLARED

# `OPS-0004`'s own vocabulary — see `RuntimeFinding.QUALIFICATIONS` for
# the full closed list.
TECHNICAL_DEBT = "OPS-0004/technical-debt"
ENERGY_INEFFICIENCY = "OPS-0004/energy-inefficiency"
SUSTAINABILITY_ANOMALY = "OPS-0004/sustainability-anomaly"
DEPLOYMENT_MISCONFIGURATION = "OPS-0004/deployment-misconfiguration"

# All four qualifications the owner confirmed for the fifth reference
# case — none excluded, unlike every domain before it.
GPU_ANOMALY_QUALIFICATIONS = (
    TECHNICAL_DEBT,
    ENERGY_INEFFICIENCY,
    SUSTAINABILITY_ANOMALY,
    DEPLOYMENT_MISCONFIGURATION,
)

# The `provider_id` `NvidiaGpuProvider.provider_id` declares.
GPU_PROVIDER = "aistack.provider.gpu.nvidia"

# The signature `RuntimeFinding.signature` cites — `OPS-0004` itself,
# the register that authors this correlation, the same role it plays
# for every other domain evaluator.
SIGNATURE = "OPS-0004"

_KIND_LABELS = {
    TEMPERATURE_CELSIUS: "temperature",
    UTILIZATION_PERCENT: "utilization",
    MEMORY_PERCENT: "memory occupancy",
}

_KIND_UNITS = {
    TEMPERATURE_CELSIUS: "°C",
    UTILIZATION_PERCENT: "%",
    MEMORY_PERCENT: "%",
}


def evaluate_gpu(anomalies: Sequence[GpuAnomaly]) -> tuple[RuntimeFinding, ...]:
    """
    One `RuntimeFinding` per GPU anomaly `find_gpu_anomalies` already
    found, citing all four qualifications the owner confirmed for
    `OPS-0004`'s fifth reference case.

    Pure: anomalies already found in, findings out — the same
    discipline every other domain evaluator holds.
    """

    return tuple(
        RuntimeFinding(
            subject=anomaly.reading.name,
            signature=SIGNATURE,
            interpretation=_interpretation(anomaly),
            remediation=_remediation(anomaly),
            confidence="Measured",
            grounding=UNDECLARED,
            evidence=(
                CitedReading(provider=GPU_PROVIDER, reading=anomaly.reading),
            ),
            qualifications=GPU_ANOMALY_QUALIFICATIONS,
        )
        for anomaly in anomalies
    )


def _observed_value(anomaly: GpuAnomaly) -> float:
    reading = anomaly.reading

    if anomaly.threshold_kind == TEMPERATURE_CELSIUS:
        return reading.temperature_celsius

    if anomaly.threshold_kind == UTILIZATION_PERCENT:
        return reading.utilization_percent

    return reading.memory_percent


def _interpretation(anomaly: GpuAnomaly) -> str:
    label = _KIND_LABELS[anomaly.threshold_kind]
    unit = _KIND_UNITS[anomaly.threshold_kind]
    observed = _observed_value(anomaly)

    return (
        f"{anomaly.reading.name}'s {label} is {observed:.1f}{unit}, at or "
        f"above its declared threshold of {anomaly.threshold_value:.1f}"
        f"{unit} — the condition OPS-0004's fifth reference case names "
        f"(technical debt, energy inefficiency, sustainability anomaly, "
        f"deployment misconfiguration)."
    )


def _remediation(anomaly: GpuAnomaly) -> str:
    if anomaly.threshold_kind == TEMPERATURE_CELSIUS:
        return (
            f"Check cooling and identify what is driving "
            f"{anomaly.reading.name}'s temperature — the condition "
            f"OPS-0004's fifth reference case names, not a one-time "
            f"reading."
        )

    return (
        f"Identify which process is driving {anomaly.reading.name}'s "
        f"{_KIND_LABELS[anomaly.threshold_kind]} and whether it is a "
        f"service correctly delegating compute to the GPU or one "
        f"running on the CPU/GPU duo without cause — the condition "
        f"OPS-0004's fifth reference case names, not a one-time "
        f"reading."
    )
