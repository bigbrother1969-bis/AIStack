"""
`Evidence` — J4, Evidence and Observation Foundation
(`claude/PLAN-J4-EVIDENCE-OBSERVATION-2026-09-10.md`).
"""

from __future__ import annotations

from aistack.contracts.correlated_finding import CorrelatedFinding
from aistack.contracts.resource_reading import ContainerCpuReading
from aistack.contracts.temperature_reading import TemperatureReading
from aistack.kernel.evidence import Evidence


def test_a_cpu_reading_is_evidence():
    assert isinstance(
        ContainerCpuReading(container="jellyfin", cpu_percent=12.3), Evidence
    )


def test_a_temperature_reading_is_evidence():
    assert isinstance(TemperatureReading(sensor="k10temp/temp1", celsius=45.0), Evidence)


def test_a_correlated_finding_is_not_evidence():
    """
    Mutation guard: `Evidence` names two of the five real contracts,
    not all of them. Widening the union to include every contract in
    `aistack.contracts` would pass this suite silently; this pins the
    boundary to one contract that must stay outside it.
    """

    finding = CorrelatedFinding(
        container="jellyfin",
        container_command="jellyfin",
        container_reference="docker ps --no-trunc",
        process_command="jellyfin",
        process_reference="docker top jellyfin",
        deployment_command=None,
        deployment_reference=None,
    )

    assert not isinstance(finding, Evidence)


def test_a_plain_object_is_not_evidence():
    assert not isinstance(object(), Evidence)
