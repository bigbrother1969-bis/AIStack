from __future__ import annotations

import subprocess
from datetime import timezone
from unittest.mock import patch

from aistack.providers.docker.events import (
    collect_docker_events,
    docker_action_of,
    enrich,
    occurred_at_of,
    stable_subject_of,
)

COMPOSE_EVENT = {
    "status": "start",
    "id": "abc123",
    "Type": "container",
    "Action": "start",
    "Actor": {
        "ID": "abc123",
        "Attributes": {
            "name": "aistack-core-1",
            "com.docker.compose.project": "aistack",
            "com.docker.compose.service": "aistack-core",
        },
    },
    "time": 1790000000,
    "timeNano": 1790000000123456789,
}

BARE_EVENT = {
    "status": "destroy",
    "Type": "container",
    "Action": "destroy",
    "Actor": {"ID": "def456", "Attributes": {"name": "some-container"}},
    "time": 1790000100,
}

NAMELESS_EVENT = {
    "Type": "container",
    "Action": "pull",
    "Actor": {"ID": "ghi789", "Attributes": {}},
}


def _run(returncode: int = 0, stdout: str = "", raises: bool = False):
    if raises:

        def _raise(*args, **kwargs):
            raise OSError("docker not found")

        return patch("subprocess.run", side_effect=_raise)

    return patch(
        "subprocess.run",
        return_value=subprocess.CompletedProcess(
            args=[], returncode=returncode, stdout=stdout, stderr=""
        ),
    )


def test_no_docker_binary_returns_no_events():
    with _run(raises=True):
        events = collect_docker_events("2026-09-28T10:00:00Z", "2026-09-28T10:00:10Z")

    assert events == []


def test_a_nonzero_return_code_returns_no_events():
    with _run(returncode=1, stdout=""):
        events = collect_docker_events("2026-09-28T10:00:00Z", "2026-09-28T10:00:10Z")

    assert events == []


def test_real_json_lines_are_parsed():
    import json

    stdout = json.dumps(COMPOSE_EVENT) + "\n" + json.dumps(BARE_EVENT) + "\n"
    with _run(stdout=stdout):
        events = collect_docker_events("2026-09-28T10:00:00Z", "2026-09-28T10:00:10Z")

    assert len(events) == 2
    assert events[0]["Action"] == "start"
    assert events[1]["Action"] == "destroy"


def test_blank_lines_and_malformed_json_are_skipped():
    import json

    stdout = "\n" + json.dumps(COMPOSE_EVENT) + "\nnot-json\n"
    with _run(stdout=stdout):
        events = collect_docker_events("2026-09-28T10:00:00Z", "2026-09-28T10:00:10Z")

    assert len(events) == 1


def test_the_since_and_until_arguments_are_passed_through():
    with _run(stdout="") as mocked:
        collect_docker_events("SINCE", "UNTIL")

    args = mocked.call_args[0][0]
    assert args[:2] == ["docker", "events"]
    assert "SINCE" in args
    assert "UNTIL" in args


def test_stable_subject_prefers_the_compose_project_and_service():
    assert stable_subject_of(COMPOSE_EVENT) == "aistack/aistack-core"


def test_stable_subject_falls_back_to_the_actor_name():
    assert stable_subject_of(BARE_EVENT) == "some-container"


def test_stable_subject_falls_back_to_the_actor_id():
    assert stable_subject_of(NAMELESS_EVENT) == "ghi789"


def test_stable_subject_never_reads_the_docker_id_when_a_name_exists():
    """
    `ADR-0011` § 3: identity must not be a Docker id when a real name
    exists — recreation always changes the id.
    """
    assert stable_subject_of(BARE_EVENT) != BARE_EVENT["Actor"]["ID"]


def test_occurred_at_prefers_time_nano_for_sub_second_precision():
    occurred_at = occurred_at_of(COMPOSE_EVENT)
    assert occurred_at.tzinfo is timezone.utc
    assert occurred_at.microsecond == 123456


def test_occurred_at_falls_back_to_whole_second_time():
    occurred_at = occurred_at_of(BARE_EVENT)
    assert occurred_at.tzinfo is timezone.utc
    assert occurred_at.microsecond == 0


def test_docker_action_reads_the_action_field():
    assert docker_action_of(COMPOSE_EVENT) == "start"


def test_docker_action_is_empty_when_absent():
    assert docker_action_of({}) == ""


def test_enrich_keeps_the_raw_event_alongside_the_derived_facts():
    enriched = enrich(COMPOSE_EVENT)

    assert enriched["subject"] == "aistack/aistack-core"
    assert enriched["action"] == "start"
    assert enriched["raw"] == COMPOSE_EVENT
    assert "occurred_at" in enriched
