from __future__ import annotations

import json
import subprocess
from unittest.mock import patch

from aistack.providers.docker.identity import (
    ContainerIdentity,
    identities_of,
    inspect_containers,
    list_running_container_names,
    stable_subject_from_labels,
)

COMPOSE_LABELS = {
    "com.docker.compose.project": "arrstack",
    "com.docker.compose.service": "gluetun",
}

INSPECT_ENTRY = {
    "Id": "sha256:abc123",
    "Name": "/arrstack-gluetun-1",
    "Config": {"Labels": COMPOSE_LABELS},
    "Mounts": [
        {"Destination": "/data"},
        {"Destination": "/gluetun"},
        {"Type": "tmpfs"},  # no Destination — must not crash
    ],
    "Image": "sha256:image-digest-1",
}

BARE_ENTRY = {
    "Id": "def456",
    "Name": "/some-container",
    "Config": {"Labels": {}},
    "Mounts": [],
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


# --- stable_subject_from_labels --------------------------------------


def test_prefers_the_compose_project_and_service():
    assert stable_subject_from_labels(COMPOSE_LABELS) == "arrstack/gluetun"


def test_falls_back_to_name_when_no_compose_labels():
    assert stable_subject_from_labels({}, name="some-container") == "some-container"


def test_falls_back_to_container_id_when_neither_labels_nor_name():
    assert stable_subject_from_labels({}, container_id="abc123") == "abc123"


def test_never_empty():
    assert stable_subject_from_labels({}) == "unknown"


def test_compose_labels_win_over_a_name_when_both_present():
    assert (
        stable_subject_from_labels(COMPOSE_LABELS, name="ignored-name")
        == "arrstack/gluetun"
    )


# --- list_running_container_names ------------------------------------


def test_no_docker_binary_returns_no_names():
    with _run(raises=True):
        assert list_running_container_names() == []


def test_a_nonzero_return_code_returns_no_names():
    with _run(returncode=1):
        assert list_running_container_names() == []


def test_names_are_split_one_per_line():
    with _run(stdout="arrstack-gluetun-1\nfrigate\n"):
        assert list_running_container_names() == ["arrstack-gluetun-1", "frigate"]


def test_blank_lines_are_skipped():
    with _run(stdout="\narrstack-gluetun-1\n\n"):
        assert list_running_container_names() == ["arrstack-gluetun-1"]


# --- inspect_containers ------------------------------------------------


def test_inspect_with_no_names_makes_no_call():
    with _run() as mocked:
        assert inspect_containers([]) == []
    mocked.assert_not_called()


def test_no_docker_binary_returns_no_entries():
    with _run(raises=True):
        assert inspect_containers(["x"]) == []


def test_a_nonzero_return_code_returns_no_entries():
    with _run(returncode=1):
        assert inspect_containers(["x"]) == []


def test_malformed_json_returns_no_entries():
    with _run(stdout="not json"):
        assert inspect_containers(["x"]) == []


def test_real_json_array_is_parsed():
    with _run(stdout=json.dumps([INSPECT_ENTRY])):
        entries = inspect_containers(["arrstack-gluetun-1"])
    assert entries == [INSPECT_ENTRY]


def test_every_name_is_passed_to_docker_inspect_in_one_call():
    with _run(stdout="[]") as mocked:
        inspect_containers(["a", "b", "c"])
    args = mocked.call_args[0][0]
    assert args == ["docker", "inspect", "a", "b", "c"]


# --- identities_of ------------------------------------------------------


def test_identities_of_resolves_compose_identity_and_mounts():
    with _run(stdout=json.dumps([INSPECT_ENTRY])):
        identities = identities_of(["arrstack-gluetun-1"])

    assert identities == [
        ContainerIdentity(
            name="arrstack-gluetun-1",
            stable_subject="arrstack/gluetun",
            mount_destinations=("/data", "/gluetun"),
            image_digest="sha256:image-digest-1",
        )
    ]


def test_identities_of_falls_back_to_name_with_no_compose_labels():
    with _run(stdout=json.dumps([BARE_ENTRY])):
        identities = identities_of(["some-container"])

    assert identities == [
        ContainerIdentity(
            name="some-container",
            stable_subject="some-container",
            mount_destinations=(),
            image_digest="",
        )
    ]


# --- image_digest (1.5's third collector, cadrage 2026-09-28) --------


def test_identities_of_captures_the_container_s_own_image_digest():
    """
    `.Image` on a container inspect — the image's own *configuration*
    digest, not a registry `RepoDigests` manifest digest (verified
    2026-09-28, `identity.py`'s own module comment) — is exactly the
    field 1.5's third collector needs for a purely local comparison.
    """
    with _run(stdout=json.dumps([INSPECT_ENTRY])):
        identities = identities_of(["arrstack-gluetun-1"])

    assert identities[0].image_digest == "sha256:image-digest-1"


def test_identities_of_defaults_to_an_empty_image_digest_when_absent():
    """`BARE_ENTRY` carries no `Image` key at all — not observed in
    practice, but `docker inspect`'s own contract does not guarantee
    it, so this must not crash."""
    with _run(stdout=json.dumps([BARE_ENTRY])):
        identities = identities_of(["some-container"])

    assert identities[0].image_digest == ""


def test_a_container_docker_ps_saw_but_inspect_no_longer_resolves_is_simply_absent():
    """
    A real race in a periodic poller: a container stops between
    `docker ps` and `docker inspect`. `inspect_containers` already
    returns only what Docker could still resolve — this asserts
    `identities_of` does not try to fabricate an identity for a name
    `docker ps` reported but `docker inspect` no longer answers for.
    """
    with _run(stdout=json.dumps([INSPECT_ENTRY])):
        identities = identities_of(["arrstack-gluetun-1", "already-gone"])

    assert len(identities) == 1
    assert identities[0].name == "arrstack-gluetun-1"


def test_identities_of_is_empty_on_total_failure():
    with _run(returncode=1):
        assert identities_of(["x"]) == []
