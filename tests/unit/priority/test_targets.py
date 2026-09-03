from aistack.priority.definition import (
    BackgroundPriorityDefinition,
    ContainerPriorityDefinition,
    CpuThresholdDetectorDefinition,
    JellyfinDetectorDefinition,
    PriorityAppDefinition,
    ResourcePriorityDefinition,
)
from aistack.priority.targets import resolve_resource_targets


def definition() -> ResourcePriorityDefinition:
    return ResourcePriorityDefinition(
        priority=(
            PriorityAppDefinition(
                container="jellyfin",
                normal_cpus=3,
                boosted_cpus=4,
                detector=JellyfinDetectorDefinition(url="http://127.0.0.1:8096"),
            ),
        ),
        background=BackgroundPriorityDefinition(
            default_throttled_cpus=0.1,
            containers=(
                ContainerPriorityDefinition(name="radarr"),
                ContainerPriorityDefinition(name="komf", normal_cpus=0.5),
            ),
        ),
        unlimited_cpus=4,
    )


def test_while_boosted_jellyfin_is_boosted_and_background_is_throttled():
    targets = resolve_resource_targets(definition(), boosted={"jellyfin": True})

    assert targets == {
        "jellyfin": 4,
        "radarr": 0.1,
        "komf": 0.1,
    }


def test_while_idle_everything_reads_back_to_its_own_normal():
    targets = resolve_resource_targets(definition(), boosted={"jellyfin": False})

    assert targets == {
        "jellyfin": 3,
        "radarr": None,
        "komf": 0.5,
    }


def test_a_missing_entry_in_boosted_reads_as_not_boosted():
    """
    The caller supplies one entry per priority app it actually
    polled; an app absent from `boosted` (a detector that raised, an
    app added to `priority` after the caller built its mapping)
    falls back to "not boosted" rather than raising a `KeyError`.
    """

    targets = resolve_resource_targets(definition(), boosted={})

    assert targets["jellyfin"] == 3
    assert targets["radarr"] is None


def test_a_container_with_no_override_is_unlimited_when_idle():
    """
    Mirrors the real infrastructure: thirteen of the fourteen
    governed containers carry no `normal_cpus` at all, and
    `resolve_resource_targets` must read that the same way
    `ContainerPriorityDefinition` itself does — absent means no
    limit, not zero.
    """

    targets = resolve_resource_targets(definition(), boosted={"jellyfin": False})

    assert targets["radarr"] is None


def test_komfs_own_normal_is_not_unlimited():
    targets = resolve_resource_targets(definition(), boosted={"jellyfin": False})

    assert targets["komf"] == 0.5


def test_a_priority_app_is_keyed_by_its_own_container_name():
    custom = ResourcePriorityDefinition(
        priority=(
            PriorityAppDefinition(
                container="jellyfin-main",
                normal_cpus=3,
                boosted_cpus=4,
                detector=JellyfinDetectorDefinition(url="http://127.0.0.1:8096"),
            ),
        ),
        background=BackgroundPriorityDefinition(default_throttled_cpus=0.1),
        unlimited_cpus=4,
    )

    targets = resolve_resource_targets(custom, boosted={"jellyfin-main": True})

    assert targets == {"jellyfin-main": 4}


def test_no_background_containers_still_resolves_the_priority_app_alone():
    empty = ResourcePriorityDefinition(
        priority=(
            PriorityAppDefinition(
                container="jellyfin",
                normal_cpus=3,
                boosted_cpus=4,
                detector=JellyfinDetectorDefinition(url="http://127.0.0.1:8096"),
            ),
        ),
        background=BackgroundPriorityDefinition(default_throttled_cpus=0.1),
        unlimited_cpus=4,
    )

    assert resolve_resource_targets(empty, boosted={"jellyfin": False}) == {
        "jellyfin": 3
    }


def two_app_definition() -> ResourcePriorityDefinition:
    return ResourcePriorityDefinition(
        priority=(
            PriorityAppDefinition(
                container="jellyfin",
                normal_cpus=3,
                boosted_cpus=4,
                detector=JellyfinDetectorDefinition(url="http://127.0.0.1:8096"),
            ),
            PriorityAppDefinition(
                container="some-app",
                normal_cpus=1,
                boosted_cpus=2,
                detector=CpuThresholdDetectorDefinition(),
            ),
        ),
        background=BackgroundPriorityDefinition(
            default_throttled_cpus=0.1,
            containers=(ContainerPriorityDefinition(name="radarr"),),
        ),
        unlimited_cpus=4,
    )


def test_each_priority_app_targets_only_its_own_boosted_state():
    """
    Decision 4 of
    `claude/PLAN-DYNAMIC-CONTAINER-PRIORITY-2026-09-03.md` —
    "chaque appli suit sa propre activité": a second, idle priority
    app is not boosted just because a different one is busy.
    """

    targets = resolve_resource_targets(
        two_app_definition(), boosted={"jellyfin": True, "some-app": False}
    )

    assert targets["jellyfin"] == 4
    assert targets["some-app"] == 1


def test_background_throttles_when_any_priority_app_is_boosted():
    targets = resolve_resource_targets(
        two_app_definition(), boosted={"jellyfin": False, "some-app": True}
    )

    assert targets["radarr"] == 0.1


def test_background_is_normal_only_once_no_priority_app_is_boosted():
    targets = resolve_resource_targets(
        two_app_definition(), boosted={"jellyfin": False, "some-app": False}
    )

    assert targets["radarr"] is None
