"""
`evaluate_gpu` — the GPU-domain analogue of `evaluate_backup`/
`evaluate_services`, citing all four `OPS-0004` qualifications from a
`GpuAnomaly` already confirmed by `find_gpu_anomalies`.
"""

from __future__ import annotations

from datetime import datetime, timezone

from aistack.contracts.gpu_anomaly import GpuAnomaly
from aistack.contracts.gpu_reading import GpuReading
from aistack.contracts.gpu_threshold import TEMPERATURE_CELSIUS, UTILIZATION_PERCENT
from aistack.contracts.runtime_finding import CitedReading
from aistack.contracts.undeclared import UNDECLARED
from aistack.runtime.evaluate_gpu import (
    DEPLOYMENT_MISCONFIGURATION,
    ENERGY_INEFFICIENCY,
    GPU_ANOMALY_QUALIFICATIONS,
    GPU_PROVIDER,
    SUSTAINABILITY_ANOMALY,
    TECHNICAL_DEBT,
    evaluate_gpu,
)

NAME = "Quadro P400"


def reading(
    name: str = NAME,
    utilization_percent: float = 95.0,
    memory_used_mib: float = 142.0,
    memory_total_mib: float = 2048.0,
    temperature_celsius: float = 85.0,
) -> GpuReading:
    return GpuReading(
        name=name,
        observed_at=datetime.now(timezone.utc),
        utilization_percent=utilization_percent,
        memory_used_mib=memory_used_mib,
        memory_total_mib=memory_total_mib,
        temperature_celsius=temperature_celsius,
    )


def hot_anomaly(name: str = NAME, temperature_celsius: float = 85.0) -> GpuAnomaly:
    return GpuAnomaly(
        reading=reading(name=name, temperature_celsius=temperature_celsius),
        threshold_kind=TEMPERATURE_CELSIUS,
        threshold_value=80.0,
    )


def busy_anomaly(name: str = NAME) -> GpuAnomaly:
    return GpuAnomaly(
        reading=reading(name=name, utilization_percent=95.0),
        threshold_kind=UTILIZATION_PERCENT,
        threshold_value=90.0,
    )


def test_no_anomalies_yields_no_findings():

    assert evaluate_gpu([]) == ()


def test_an_anomaly_is_qualified_with_all_four_terms():

    findings = evaluate_gpu([hot_anomaly()])

    assert len(findings) == 1
    assert findings[0].qualifications == GPU_ANOMALY_QUALIFICATIONS
    assert findings[0].qualifications == (
        TECHNICAL_DEBT,
        ENERGY_INEFFICIENCY,
        SUSTAINABILITY_ANOMALY,
        DEPLOYMENT_MISCONFIGURATION,
    )


def test_the_finding_subject_is_the_gpu_name():

    findings = evaluate_gpu([hot_anomaly(name=NAME)])

    assert findings[0].subject == NAME


def test_the_finding_cites_ops_0004_as_its_signature():

    findings = evaluate_gpu([hot_anomaly()])

    assert findings[0].signature == "OPS-0004"


def test_the_confidence_reflects_a_measured_reading():

    findings = evaluate_gpu([hot_anomaly()])

    assert findings[0].confidence == "Measured"


def test_the_finding_starts_ungrounded_like_any_other():

    findings = evaluate_gpu([hot_anomaly()])

    assert findings[0].grounding == UNDECLARED


def test_the_evidence_cites_the_gpu_provider_and_the_reading():

    anomaly = hot_anomaly()
    findings = evaluate_gpu([anomaly])

    evidence = findings[0].evidence
    assert len(evidence) == 1
    assert isinstance(evidence[0], CitedReading)
    assert evidence[0].provider == GPU_PROVIDER
    assert evidence[0].reading == anomaly.reading


def test_a_temperature_interpretation_states_the_value_and_threshold():

    findings = evaluate_gpu([hot_anomaly(temperature_celsius=85.0)])

    interpretation = findings[0].interpretation
    assert "85.0°C" in interpretation
    assert "80.0°C" in interpretation
    assert "technical debt" in interpretation
    assert "energy inefficiency" in interpretation
    assert "sustainability anomaly" in interpretation
    assert "deployment misconfiguration" in interpretation


def test_a_utilization_interpretation_states_the_value_and_threshold():

    findings = evaluate_gpu([busy_anomaly()])

    interpretation = findings[0].interpretation
    assert "95.0%" in interpretation
    assert "90.0%" in interpretation


def test_one_finding_per_anomaly():

    findings = evaluate_gpu(
        [hot_anomaly(name="Quadro P400"), busy_anomaly(name="Tesla T4")]
    )

    assert {f.subject for f in findings} == {"Quadro P400", "Tesla T4"}
    assert all(f.qualifications == GPU_ANOMALY_QUALIFICATIONS for f in findings)
