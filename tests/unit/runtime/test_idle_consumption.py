import pytest

from aistack.contracts.resource_reading import ContainerCpuReading
from aistack.contracts.unexplained_consumption import UnexplainedConsumption
from aistack.priority.definition import (
    BackgroundPriorityDefinition,
    ContainerPriorityDefinition,
    CpuThresholdDetectorDefinition,
    PriorityAppDefinition,
    ResourcePriorityDefinition,
)
from aistack.runtime.idle_consumption import find_unexplained_consumption


def definition(
    *, priority: tuple = (), background: tuple = ()
) -> ResourcePriorityDefinition:
    return ResourcePriorityDefinition(
        priority=priority,
        background=BackgroundPriorityDefinition(
            default_throttled_cpus=0.1, containers=background
        ),
        unlimited_cpus=4.0,
    )


JELLYFIN = PriorityAppDefinition(
    container="jellyfin",
    normal_cpus=3.0,
    boosted_cpus=4.0,
    detector=CpuThresholdDetectorDefinition(),
)

SONARR = ContainerPriorityDefinition(name="sonarr")


# --------------------------------------------------------------------
# `ContainerCpuReading` / `UnexplainedConsumption` themselves
# --------------------------------------------------------------------


def test_a_reading_requires_a_container_name():

    with pytest.raises(ValueError, match="names none"):
        ContainerCpuReading(container="", cpu_percent=5.0)


def test_a_reading_refuses_negative_cpu():

    with pytest.raises(ValueError, match="negative"):
        ContainerCpuReading(container="x", cpu_percent=-1.0)


def test_a_finding_below_threshold_is_refused_by_its_own_contract():
    """
    `UnexplainedConsumption` enforces the same rule its only
    producer already applies — the same reasoning `RuntimeFinding`
    enforces non-empty evidence in the constructor, not in the
    caller.
    """

    with pytest.raises(ValueError, match="not what the threshold names"):
        UnexplainedConsumption(
            container="x", cpu_percent=1.0, threshold_percent=5.0
        )


# --------------------------------------------------------------------
# `find_unexplained_consumption`
# --------------------------------------------------------------------


def test_an_undeclared_container_over_threshold_is_flagged():

    findings = find_unexplained_consumption(
        [ContainerCpuReading(container="aistack-selection-ui", cpu_percent=52.0)],
        definition(),
        threshold_percent=5.0,
    )

    assert len(findings) == 1
    assert findings[0].container == "aistack-selection-ui"
    assert findings[0].cpu_percent == 52.0


def test_an_undeclared_container_under_threshold_is_not_flagged():

    findings = find_unexplained_consumption(
        [ContainerCpuReading(container="some-cron", cpu_percent=0.2)],
        definition(),
        threshold_percent=5.0,
    )

    assert findings == ()


def test_a_priority_app_is_never_flagged_however_high_its_reading():

    findings = find_unexplained_consumption(
        [ContainerCpuReading(container="jellyfin", cpu_percent=99.0)],
        definition(priority=(JELLYFIN,)),
        threshold_percent=5.0,
    )

    assert findings == ()


def test_a_background_container_is_never_flagged_however_high_its_reading():

    findings = find_unexplained_consumption(
        [ContainerCpuReading(container="sonarr", cpu_percent=99.0)],
        definition(background=(SONARR,)),
        threshold_percent=5.0,
    )

    assert findings == ()


def test_a_background_container_with_no_normal_cpus_is_still_declared():
    """
    `normal_cpus: None` means "no limit at rest", not "nobody
    looked". Declared membership is presence in the list, never
    whether a value happens to be set.
    """

    findings = find_unexplained_consumption(
        [ContainerCpuReading(container="sonarr", cpu_percent=50.0)],
        definition(background=(ContainerPriorityDefinition(name="sonarr"),)),
        threshold_percent=5.0,
    )

    assert findings == ()


def test_a_reading_exactly_at_the_threshold_is_flagged():

    findings = find_unexplained_consumption(
        [ContainerCpuReading(container="x", cpu_percent=5.0)],
        definition(),
        threshold_percent=5.0,
    )

    assert len(findings) == 1


def test_only_the_undeclared_reading_in_a_batch_is_flagged():

    findings = find_unexplained_consumption(
        [
            ContainerCpuReading(container="jellyfin", cpu_percent=90.0),
            ContainerCpuReading(container="aistack-selection-ui", cpu_percent=52.0),
            ContainerCpuReading(container="sonarr", cpu_percent=0.1),
        ],
        definition(priority=(JELLYFIN,), background=(SONARR,)),
        threshold_percent=5.0,
    )

    assert [f.container for f in findings] == ["aistack-selection-ui"]


def test_an_empty_reading_set_flags_nothing():

    assert find_unexplained_consumption([], definition()) == ()


def test_the_default_threshold_is_used_when_none_is_given():

    from aistack.runtime.idle_consumption import DEFAULT_THRESHOLD_PERCENT

    findings = find_unexplained_consumption(
        [ContainerCpuReading(container="x", cpu_percent=DEFAULT_THRESHOLD_PERCENT)],
        definition(),
    )

    assert len(findings) == 1
    assert findings[0].threshold_percent == DEFAULT_THRESHOLD_PERCENT
