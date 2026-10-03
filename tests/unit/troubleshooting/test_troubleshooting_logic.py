"""`aistack.troubleshooting` — the routing key, and the one fix."""

from __future__ import annotations

from aistack.contracts.resource_reading import ContainerCpuReading
from aistack.contracts.runtime_finding import CitedReading, RuntimeFinding
from aistack.priority.definition import (
    BackgroundPriorityDefinition,
    ContainerPriorityDefinition,
    CpuThresholdDetectorDefinition,
    PriorityAppDefinition,
    ResourcePriorityDefinition,
)
from aistack.troubleshooting.apply import BackgroundChange, class_as_background
from aistack.troubleshooting.findings import CONSUMPTION_DOMAIN, qualify


def finding(subject: str) -> RuntimeFinding:
    return RuntimeFinding(
        subject=subject,
        signature="OPS-0001/S-003",
        interpretation="unexplained CPU consumption",
        remediation=f"declare {subject} in resource_priority.yml",
        confidence="high",
        grounding=f"OPS-0003/{subject}",
        evidence=(
            CitedReading(
                provider="aistack.provider.docker",
                reading=ContainerCpuReading(container=subject, cpu_percent=12.2),
            ),
        ),
        qualifications=("OPS-0004/sustainability-anomaly",),
    )


DEFINITION = ResourcePriorityDefinition(
    priority=(
        PriorityAppDefinition(
            container="jellyfin",
            normal_cpus=3.0,
            boosted_cpus=4.0,
            detector=CpuThresholdDetectorDefinition(threshold_percent=50.0, sustained_seconds=15.0),
        ),
    ),
    background=BackgroundPriorityDefinition(
        default_throttled_cpus=0.1,
        containers=(ContainerPriorityDefinition(name="sonarr"),),
    ),
    unlimited_cpus=4.0,
    grace_seconds=60.0,
)


def test_a_unique_subject_keeps_its_bare_name_as_key():
    (entry,) = qualify([(CONSUMPTION_DOMAIN, finding("booklore_db"))])

    assert entry.key == "booklore_db"
    assert entry.applyable


def test_a_shared_subject_is_keyed_by_its_domain():
    entries = qualify([("Tests PRA", finding("nextcloud")), ("État persistant", finding("nextcloud"))])

    assert [entry.key for entry in entries] == ["Tests PRA::nextcloud", "État persistant::nextcloud"]
    assert all(entry.finding.subject == "nextcloud" for entry in entries)


def test_only_a_consumption_finding_may_be_fixed_by_a_click():
    (entry,) = qualify([("Tests PRA", finding("nextcloud"))])

    assert not entry.applyable


def test_a_new_subject_joins_the_background_list_in_order():
    decision = class_as_background(DEFINITION, "booklore_db")

    assert decision.change is BackgroundChange.ADDED
    assert decision.updated is not None
    assert [c.name for c in decision.updated.background.containers] == ["booklore_db", "sonarr"]
    assert decision.updated.priority == DEFINITION.priority
    assert decision.updated.grace_seconds == 60.0


def test_a_subject_already_in_the_background_writes_nothing():
    decision = class_as_background(DEFINITION, "sonarr")

    assert decision.change is BackgroundChange.ALREADY_BACKGROUND
    assert decision.updated is None


def test_a_priority_application_is_never_demoted_by_a_click():
    decision = class_as_background(DEFINITION, "jellyfin")

    assert decision.change is BackgroundChange.REFUSED_PRIORITY
    assert decision.updated is None
