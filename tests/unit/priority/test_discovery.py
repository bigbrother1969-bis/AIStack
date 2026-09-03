from aistack.priority.discovery import (
    DiscoveredContainer,
    resolve_discovered_containers,
)


def observation(containers: list[dict]) -> dict:
    return {"docker": {"containers": containers}}


def test_a_running_container_is_shaped_with_running_true():
    discovered = resolve_discovered_containers(
        observation(
            [
                {
                    "Names": "jellyfin",
                    "Image": "jellyfin/jellyfin",
                    "State": "running",
                    "Status": "Up 3 days",
                }
            ]
        )
    )

    assert discovered == (
        DiscoveredContainer(
            name="jellyfin",
            image="jellyfin/jellyfin",
            running=True,
            status="Up 3 days",
        ),
    )


def test_a_stopped_container_is_kept_with_running_false():
    """
    `docker ps -a`, not `docker ps` — a container the owner has
    stopped is still one they may want to classify.
    """

    discovered = resolve_discovered_containers(
        observation(
            [{"Names": "radarr", "Image": "radarr", "State": "exited", "Status": "Exited (0) 2 hours ago"}]
        )
    )

    assert discovered[0].running is False


def test_results_are_sorted_by_name():
    discovered = resolve_discovered_containers(
        observation(
            [
                {"Names": "sonarr", "Image": "x", "State": "running", "Status": ""},
                {"Names": "bazarr", "Image": "x", "State": "running", "Status": ""},
            ]
        )
    )

    assert [c.name for c in discovered] == ["bazarr", "sonarr"]


def test_a_multi_name_container_keeps_only_its_primary_name():
    discovered = resolve_discovered_containers(
        observation(
            [
                {
                    "Names": "radarr,radarr-old",
                    "Image": "x",
                    "State": "running",
                    "Status": "",
                }
            ]
        )
    )

    assert discovered[0].name == "radarr"


def test_a_container_with_no_name_is_dropped():
    discovered = resolve_discovered_containers(
        observation([{"Names": "", "Image": "x", "State": "running", "Status": ""}])
    )

    assert discovered == ()


def test_no_containers_at_all_resolves_to_empty():
    assert resolve_discovered_containers(observation([])) == ()


def test_a_missing_docker_block_resolves_to_empty():
    assert resolve_discovered_containers({}) == ()
