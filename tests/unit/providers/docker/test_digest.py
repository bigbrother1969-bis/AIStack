from __future__ import annotations

import json
import subprocess
from unittest.mock import patch

from aistack.providers.docker.digest import collect_running_container_digests

INSPECT_ENTRY = {
    "Id": "abc123",
    "Name": "/arrstack-gluetun-1",
    "Config": {
        "Labels": {
            "com.docker.compose.project": "arrstack",
            "com.docker.compose.service": "gluetun",
        }
    },
    "Mounts": [],
    "Image": "sha256:image-digest-1",
}

NO_DIGEST_ENTRY = {
    "Id": "def456",
    "Name": "/some-container",
    "Config": {"Labels": {}},
    "Mounts": [],
}


def _fake_run(ps_stdout: str, inspect_stdout: str):
    def _run(args, **kwargs):
        if args[:2] == ["docker", "ps"]:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout=ps_stdout, stderr="")
        if args[:2] == ["docker", "inspect"]:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout=inspect_stdout, stderr="")
        raise AssertionError(f"unexpected call: {args}")

    return patch("subprocess.run", side_effect=_run)


def test_no_running_containers_produces_no_digests():
    with _fake_run(ps_stdout="", inspect_stdout="[]"):
        assert collect_running_container_digests() == []


def test_a_running_container_s_digest_is_collected_under_its_stable_subject():
    with _fake_run(ps_stdout="arrstack-gluetun-1\n", inspect_stdout=json.dumps([INSPECT_ENTRY])):
        results = collect_running_container_digests()

    assert results == [{"subject": "arrstack/gluetun", "digest": "sha256:image-digest-1"}]


def test_a_container_with_no_observable_digest_is_skipped_not_recorded_empty():
    """
    An empty `image_digest` is the absence of an observation, not a
    real one — `aistack.providers.docker.digest`'s own module comment
    explains why this is skipped rather than yielding
    `{"subject": ..., "digest": ""}`.
    """
    with _fake_run(ps_stdout="some-container\n", inspect_stdout=json.dumps([NO_DIGEST_ENTRY])):
        assert collect_running_container_digests() == []


def test_two_running_containers_each_get_their_own_entry():
    second_entry = dict(
        INSPECT_ENTRY,
        Name="/frigate",
        Config={"Labels": {}},
        Image="sha256:image-digest-2",
    )
    with _fake_run(
        ps_stdout="arrstack-gluetun-1\nfrigate\n",
        inspect_stdout=json.dumps([INSPECT_ENTRY, second_entry]),
    ):
        results = collect_running_container_digests()

    assert results == [
        {"subject": "arrstack/gluetun", "digest": "sha256:image-digest-1"},
        {"subject": "frigate", "digest": "sha256:image-digest-2"},
    ]
