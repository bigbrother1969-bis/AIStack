from aistack.priority.definition import (
    BackgroundPriorityDefinition,
    ContainerPriorityDefinition,
    JellyfinPriorityDefinition,
    ResourcePriorityDefinition,
)
from aistack.priority.targets import resolve_resource_targets


def definition() -> ResourcePriorityDefinition:
    return ResourcePriorityDefinition(
        jellyfin=JellyfinPriorityDefinition(
            container="jellyfin", normal_cpus=3, boosted_cpus=4
        ),
        background=BackgroundPriorityDefinition(
            default_throttled_cpus=0.1,
            containers=(
                ContainerPriorityDefinition(name="radarr"),
                ContainerPriorityDefinition(name="komf", normal_cpus=0.5),
            ),
        ),
    )


def test_while_playing_jellyfin_is_boosted_and_background_is_throttled():
    targets = resolve_resource_targets(definition(), playing=True)

    assert targets == {
        "jellyfin": 4,
        "radarr": 0.1,
        "komf": 0.1,
    }


def test_while_idle_everything_reads_back_to_its_own_normal():
    targets = resolve_resource_targets(definition(), playing=False)

    assert targets == {
        "jellyfin": 3,
        "radarr": None,
        "komf": 0.5,
    }


def test_a_container_with_no_override_is_unlimited_when_idle():
    """
    Mirrors the real infrastructure: thirteen of the fourteen
    governed containers carry no `normal_cpus` at all, and
    `resolve_resource_targets` must read that the same way
    `ContainerPriorityDefinition` itself does — absent means no
    limit, not zero.
    """

    targets = resolve_resource_targets(definition(), playing=False)

    assert targets["radarr"] is None


def test_komfs_own_normal_is_not_unlimited():
    targets = resolve_resource_targets(definition(), playing=False)

    assert targets["komf"] == 0.5


def test_jellyfin_is_keyed_by_its_own_container_name():
    custom = ResourcePriorityDefinition(
        jellyfin=JellyfinPriorityDefinition(
            container="jellyfin-main", normal_cpus=3, boosted_cpus=4
        ),
        background=BackgroundPriorityDefinition(default_throttled_cpus=0.1),
    )

    targets = resolve_resource_targets(custom, playing=True)

    assert targets == {"jellyfin-main": 4}


def test_no_background_containers_still_resolves_jellyfin_alone():
    empty = ResourcePriorityDefinition(
        jellyfin=JellyfinPriorityDefinition(
            container="jellyfin", normal_cpus=3, boosted_cpus=4
        ),
        background=BackgroundPriorityDefinition(default_throttled_cpus=0.1),
    )

    assert resolve_resource_targets(empty, playing=False) == {"jellyfin": 3}
