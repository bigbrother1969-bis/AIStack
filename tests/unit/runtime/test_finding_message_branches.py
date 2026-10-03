"""
The sentence branches no other evaluator test reaches, built here so
`conftest.py` checks them against the catalogs like every other one
(ADR-0010 § 4, revised 2026-10-03).
"""

from __future__ import annotations

from datetime import datetime, timezone

from aistack.contracts.container_distress import RESTARTING, UNHEALTHY, ContainerDistress
from aistack.contracts.container_health import ContainerHealth
from aistack.contracts.container_state_reading import ContainerStateReading
from aistack.contracts.gpu_anomaly import GpuAnomaly
from aistack.contracts.gpu_reading import GpuReading
from aistack.contracts.gpu_threshold import MEMORY_PERCENT
from aistack.contracts.temperature_reading import TemperatureReading
from aistack.contracts.unexplained_consumption import UnexplainedConsumption
from aistack.i18n import translator_for
from aistack.i18n.findings import finding_interpretation, finding_remediation
from aistack.runtime.evaluate import evaluate
from aistack.runtime.evaluate_gpu import evaluate_gpu
from aistack.runtime.evaluate_services import evaluate_services


def test_a_gpu_memory_anomaly_has_its_own_sentence():
    (finding,) = evaluate_gpu(
        [
            GpuAnomaly(
                reading=GpuReading(
                    name="Quadro P400",
                    observed_at=datetime.now(timezone.utc),
                    utilization_percent=5.0,
                    memory_used_mib=1900.0,
                    memory_total_mib=2048.0,
                    temperature_celsius=40.0,
                ),
                threshold_kind=MEMORY_PERCENT,
                threshold_value=90.0,
            )
        ]
    )

    assert "occupation mémoire" in finding_interpretation(finding, translator_for("fr"))


def test_an_unhealthy_container_and_one_both_restarting_and_unhealthy():
    readings = [
        ContainerDistress(
            reading=ContainerStateReading(
                container="immich", state="running", health=ContainerHealth.UNHEALTHY
            ),
            reasons=(UNHEALTHY,),
        ),
        ContainerDistress(
            reading=ContainerStateReading(
                container="gluetun", state="restarting", health=ContainerHealth.UNHEALTHY
            ),
            reasons=(RESTARTING, UNHEALTHY),
        ),
    ]

    unhealthy, both = evaluate_services(readings)
    t = translator_for("fr")

    assert "en mauvaise santé" in finding_interpretation(unhealthy, t)
    assert "en train de redémarrer et en mauvaise santé" in finding_interpretation(both, t)


def test_several_hot_sensors_are_counted_in_the_reader_s_language():
    hot = [
        TemperatureReading(sensor="chip-a/temp1", celsius=71.0, high_celsius=70.0),
        TemperatureReading(sensor="chip-b/temp1", celsius=72.0, high_celsius=70.0),
    ]

    (finding,) = evaluate(
        [UnexplainedConsumption(container="firefly", cpu_percent=52.0, threshold_percent=5.0)],
        hot,
    )
    t = translator_for("fr")

    assert "et 1 autre(s) capteur(s)" in finding_interpretation(finding, t)
    assert "refroidissement" in finding_remediation(finding, t)
