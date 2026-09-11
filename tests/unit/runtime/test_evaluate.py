"""
`evaluate` — J5, `claude/PLAN-TRAJECTOIRE-2026-09-04.md`: the first
correlation of `ContainerCpuReading`-derived and `TemperatureReading`
evidence into a qualified `RuntimeFinding`.
"""

from __future__ import annotations

from aistack.contracts.resource_reading import ContainerCpuReading
from aistack.contracts.runtime_finding import CitedReading
from aistack.contracts.temperature_reading import TemperatureReading
from aistack.contracts.undeclared import UNDECLARED
from aistack.contracts.unexplained_consumption import UnexplainedConsumption
from aistack.runtime.evaluate import (
    ENERGY_INEFFICIENCY,
    SUSTAINABILITY_ANOMALY,
    evaluate,
)


def consumption(container: str = "aistack-selection-ui", cpu_percent: float = 52.0):
    return UnexplainedConsumption(
        container=container, cpu_percent=cpu_percent, threshold_percent=5.0
    )


def hot_reading(sensor: str = "k10temp-pci-00c3/temp1") -> TemperatureReading:
    return TemperatureReading(sensor=sensor, celsius=70.5, high_celsius=70.0)


def cool_reading() -> TemperatureReading:
    return TemperatureReading(sensor="acpitz-acpi-0/temp1", celsius=45.0, high_celsius=70.0)


def undeclared_threshold_reading() -> TemperatureReading:
    return TemperatureReading(sensor="unknown-chip/temp1", celsius=99.0)


# --------------------------------------------------------------------
# No consumption, no finding
# --------------------------------------------------------------------


def test_no_consumption_yields_no_findings_however_hot_the_host():

    findings = evaluate([], [hot_reading()])

    assert findings == ()


# --------------------------------------------------------------------
# Consumption alone: energy inefficiency, never sustainability anomaly
# --------------------------------------------------------------------


def test_unexplained_consumption_alone_is_qualified_energy_inefficiency():

    findings = evaluate([consumption()], [])

    assert len(findings) == 1
    finding = findings[0]
    assert finding.qualifications == (ENERGY_INEFFICIENCY,)


def test_a_cool_host_does_not_add_sustainability_anomaly():

    findings = evaluate([consumption()], [cool_reading()])

    assert findings[0].qualifications == (ENERGY_INEFFICIENCY,)


def test_an_undeclared_threshold_does_not_correlate_as_hot():
    """
    `at_or_above_high`/`at_or_above_critical` return `None`, not
    `False`, for a sensor with no declared threshold — absent is not
    zero, and this must not be read as "definitely not hot" turning
    into "definitely hot" either.
    """

    findings = evaluate([consumption()], [undeclared_threshold_reading()])

    assert findings[0].qualifications == (ENERGY_INEFFICIENCY,)


# --------------------------------------------------------------------
# Consumption + a hot reading: both qualifications, correlated
# --------------------------------------------------------------------


def test_consumption_with_a_hot_host_is_qualified_both_ways():

    findings = evaluate([consumption()], [hot_reading()])

    finding = findings[0]
    assert finding.qualifications == (ENERGY_INEFFICIENCY, SUSTAINABILITY_ANOMALY)


def test_the_qualifications_cite_ops_0004():

    findings = evaluate([consumption()], [hot_reading()])

    assert all(q.startswith("OPS-0004/") for q in findings[0].qualifications)


def test_the_finding_subject_is_the_consuming_container():

    findings = evaluate([consumption(container="firefly")], [hot_reading()])

    assert findings[0].subject == "firefly"


def test_a_critical_reading_with_no_high_declared_still_correlates():

    critical_only = TemperatureReading(
        sensor="chip/temp1", celsius=90.0, critical_celsius=85.0
    )

    findings = evaluate([consumption()], [critical_only])

    assert findings[0].qualifications == (ENERGY_INEFFICIENCY, SUSTAINABILITY_ANOMALY)


# --------------------------------------------------------------------
# Evidence: what is cited, and by whom
# --------------------------------------------------------------------


def test_the_cpu_evidence_cites_the_docker_provider():

    findings = evaluate([consumption()], [])

    evidence = findings[0].evidence
    assert len(evidence) == 1
    assert isinstance(evidence[0], CitedReading)
    assert evidence[0].provider == "aistack.provider.docker"
    assert evidence[0].reading == ContainerCpuReading(
        container="aistack-selection-ui", cpu_percent=52.0
    )


def test_a_hot_reading_adds_a_second_cited_evidence_item():

    findings = evaluate([consumption()], [hot_reading()])

    evidence = findings[0].evidence
    assert len(evidence) == 2
    assert evidence[1].provider == "aistack.provider.host"
    assert evidence[1].reading == hot_reading()


def test_every_hot_reading_is_cited_not_only_the_first():

    findings = evaluate([consumption()], [hot_reading("chip-a/temp1"), hot_reading("chip-b/temp1")])

    evidence = findings[0].evidence
    assert len(evidence) == 3
    cited_sensors = {item.reading.sensor for item in evidence[1:]}
    assert cited_sensors == {"chip-a/temp1", "chip-b/temp1"}


# --------------------------------------------------------------------
# The rest of the shape
# --------------------------------------------------------------------


def test_the_finding_cites_ops_0004_as_its_signature():

    findings = evaluate([consumption()], [])

    assert findings[0].signature == "OPS-0004"


def test_the_finding_starts_ungrounded_like_any_other():
    """
    Grounding against `OPS-0003` is `ground_findings`'s job, applied
    uniformly by `runtime_diagnose` after every finding is built —
    `evaluate` does not pre-empt it.
    """

    findings = evaluate([consumption()], [])

    assert findings[0].grounding == UNDECLARED


def test_the_confidence_reflects_a_measured_reading_not_a_declared_rule():

    findings = evaluate([consumption()], [])

    assert findings[0].confidence == "Measured"


def test_one_finding_per_container_with_unexplained_consumption():

    findings = evaluate(
        [consumption(container="a"), consumption(container="b")], [hot_reading()]
    )

    assert {f.subject for f in findings} == {"a", "b"}
    assert all(f.qualifications == (ENERGY_INEFFICIENCY, SUSTAINABILITY_ANOMALY) for f in findings)
