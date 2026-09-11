"""
`Observation` — J4, Evidence and Observation Foundation.
"""

from __future__ import annotations

from datetime import datetime, timezone

from aistack.contracts.resource_reading import ContainerCpuReading
from aistack.contracts.runtime_observation import RuntimeObservation
from aistack.kernel.evidence import Observation


def test_a_runtime_observation_is_an_observation():
    observation = RuntimeObservation(
        subject="jellyfin",
        provider="aistack.provider.docker",
        state="running",
        collected_at=datetime.now(timezone.utc),
        depth=0,
    )

    assert isinstance(observation, Observation)


def test_evidence_is_not_an_observation():
    """
    Mutation guard, the reverse of `Observation`'s only member being
    `RuntimeObservation`: `Evidence` is what a collector produces,
    `Observation` is what a normalizer produces from it, and
    aliasing one to the other would erase that ARC-P-013 boundary
    without a single test noticing.
    """

    reading = ContainerCpuReading(container="jellyfin", cpu_percent=12.3)

    assert not isinstance(reading, Observation)
