"""
Turn `GpuAnomaly`s (`OPS-0007` thresholds crossed) into `RuntimeFinding`s
carrying all four `OPS-0004` qualifications.
"""

from __future__ import annotations

from aistack.contracts.finding_message import FindingMessage, part

from collections.abc import Sequence

from aistack.contracts.gpu_anomaly import GpuAnomaly
from aistack.contracts.gpu_threshold import (
    MEMORY_PERCENT,
    TEMPERATURE_CELSIUS,
    UTILIZATION_PERCENT,
)
from aistack.contracts.runtime_finding import CitedReading, RuntimeFinding
from aistack.contracts.undeclared import UNDECLARED

# `OPS-0004` vocabulary; `RuntimeFinding.QUALIFICATIONS` holds the full list.
TECHNICAL_DEBT = "OPS-0004/technical-debt"
ENERGY_INEFFICIENCY = "OPS-0004/energy-inefficiency"
SUSTAINABILITY_ANOMALY = "OPS-0004/sustainability-anomaly"
DEPLOYMENT_MISCONFIGURATION = "OPS-0004/deployment-misconfiguration"

GPU_ANOMALY_QUALIFICATIONS = (
    TECHNICAL_DEBT,
    ENERGY_INEFFICIENCY,
    SUSTAINABILITY_ANOMALY,
    DEPLOYMENT_MISCONFIGURATION,
)

# The `provider_id` `NvidiaGpuProvider.provider_id` declares.
GPU_PROVIDER = "aistack.provider.gpu.nvidia"

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
    """One `RuntimeFinding` per GPU anomaly."""

    return tuple(
        RuntimeFinding(
            subject=anomaly.reading.name,
            signature=SIGNATURE,
            interpretation=_interpretation(anomaly),
            remediation=_remediation(anomaly),
            message=_message(anomaly),
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


# One catalog key per measured kind, so each language words its own label
# and unit.
_KIND_KEYS = {
    TEMPERATURE_CELSIUS: "findings.gpu.temperature",
    UTILIZATION_PERCENT: "findings.gpu.utilization",
    MEMORY_PERCENT: "findings.gpu.memory",
}


def _message(anomaly: GpuAnomaly) -> FindingMessage:
    """The same two sentences as `_interpretation`/`_remediation`, as catalog keys."""

    key = _KIND_KEYS[anomaly.threshold_kind]
    name = anomaly.reading.name

    return FindingMessage(
        interpretation=(
            part(
                f"{key}.interpretation",
                name=name,
                observed=f"{_observed_value(anomaly):.1f}",
                threshold=f"{anomaly.threshold_value:.1f}",
            ),
        ),
        remediation=(part(f"{key}.remediation", name=name),),
    )
