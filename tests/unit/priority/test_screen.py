"""`aistack.priority.screen` — the join the screen shows, the definition its form describes."""

from __future__ import annotations

import pytest

from aistack.priority.definition import (
    BackgroundPriorityDefinition,
    ContainerPriorityDefinition,
    CpuThresholdDetectorDefinition,
    JellyfinDetectorDefinition,
    PriorityAppDefinition,
    ResourcePriorityDefinition,
)
from aistack.priority.discovery import DiscoveredContainer
from aistack.priority.screen import definition_from_form, priority_rows

JELLYFIN = PriorityAppDefinition(
    container="jellyfin",
    normal_cpus=3.0,
    boosted_cpus=4.0,
    detector=JellyfinDetectorDefinition(
        url="http://127.0.0.1:8096", api_key_env="JELLYFIN_API_KEY", timeout_seconds=5.0
    ),
)

DEFINITION = ResourcePriorityDefinition(
    priority=(JELLYFIN,),
    background=BackgroundPriorityDefinition(
        default_throttled_cpus=0.1,
        containers=(ContainerPriorityDefinition(name="sonarr", normal_cpus=None),),
    ),
    unlimited_cpus=4.0,
    grace_seconds=60.0,
)

DISCOVERED = (
    DiscoveredContainer(name="jellyfin", image="jellyfin/jellyfin", running=True, status="Up 3 days"),
    DiscoveredContainer(name="nginx", image="nginx", running=False, status="Exited (0)"),
)


def test_every_name_from_docker_and_the_definition_is_a_row_in_order():
    rows = priority_rows(DEFINITION, DISCOVERED)

    assert [row.name for row in rows] == ["jellyfin", "nginx", "sonarr"]


def test_each_row_carries_its_classification():
    rows = {row.name: row for row in priority_rows(DEFINITION, DISCOVERED)}

    assert rows["jellyfin"].classification == "priority"
    assert rows["jellyfin"].priority_app == JELLYFIN
    assert rows["sonarr"].classification == "throttled"
    assert rows["nginx"].classification == "ignored"


def test_a_name_docker_does_not_report_is_kept_with_an_unknown_state():
    sonarr = {row.name: row for row in priority_rows(DEFINITION, DISCOVERED)}["sonarr"]

    assert sonarr.running is None
    assert sonarr.image == ""


def test_nothing_discovered_still_shows_the_definition():
    assert [row.name for row in priority_rows(DEFINITION, ())] == ["jellyfin", "sonarr"]


def test_the_form_classifies_and_sorts_each_shown_name():
    updated = definition_from_form(
        DEFINITION,
        {"jellyfin", "nginx", "sonarr"},
        {
            "classification__nginx": "priority",
            "normal_cpus__nginx": "1",
            "boosted_cpus__nginx": "2",
            "detector_type__nginx": "cpu_threshold",
            "cpu_threshold_percent__nginx": "70",
            "cpu_sustained_seconds__nginx": "",
            "classification__jellyfin": "throttled",
            "throttled_normal_cpus__jellyfin": "0.5",
        },
    )

    assert [app.container for app in updated.priority] == ["nginx"]
    nginx = updated.priority[0]
    assert (nginx.normal_cpus, nginx.boosted_cpus) == (1.0, 2.0)
    assert nginx.detector == CpuThresholdDetectorDefinition(threshold_percent=70.0, sustained_seconds=15.0)
    assert updated.background.containers == (
        ContainerPriorityDefinition(name="jellyfin", normal_cpus=0.5),
    )


def test_a_name_left_unclassified_is_ignored():
    updated = definition_from_form(DEFINITION, {"jellyfin", "sonarr"}, {})

    assert updated.priority == ()
    assert updated.background.containers == ()


def test_what_the_form_does_not_carry_is_kept():
    updated = definition_from_form(DEFINITION, {"jellyfin"}, {})

    assert updated.unlimited_cpus == 4.0
    assert updated.grace_seconds == 60.0
    assert updated.background.default_throttled_cpus == 0.1


def test_a_jellyfin_detector_is_read_from_its_own_fields():
    updated = definition_from_form(
        DEFINITION,
        {"jellyfin"},
        {
            "classification__jellyfin": "priority",
            "normal_cpus__jellyfin": "3",
            "boosted_cpus__jellyfin": "4",
            "jellyfin_url__jellyfin": "http://127.0.0.1:8096",
            "jellyfin_api_key_env__jellyfin": "JELLYFIN_API_KEY",
            "jellyfin_timeout__jellyfin": "not a number",
        },
    )

    assert updated.priority == (JELLYFIN,)


def test_a_throttle_that_is_not_a_number_is_refused_not_guessed():
    with pytest.raises(ValueError):
        definition_from_form(
            DEFINITION,
            {"sonarr"},
            {"classification__sonarr": "throttled", "throttled_normal_cpus__sonarr": "1,5"},
        )
