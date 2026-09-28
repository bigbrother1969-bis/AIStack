from __future__ import annotations

import json
import subprocess
from unittest.mock import patch

from aistack.providers.docker.diff import (
    collect_docker_diff,
    collect_running_container_diffs,
)

INSPECT_ENTRY = {
    "Id": "abc123",
    "Name": "/arrstack-gluetun-1",
    "Config": {
        "Labels": {
            "com.docker.compose.project": "arrstack",
            "com.docker.compose.service": "gluetun",
        }
    },
    "Mounts": [{"Destination": "/gluetun"}],
}

RAW_DIFF_OUTPUT = (
    "C /etc/hosts\n"
    "A /gluetun/wg0.conf\n"
    "A /run/nginx.pid\n"
    "D /var/log/old_file\n"
)


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


# --- collect_docker_diff -------------------------------------------------


def test_no_docker_binary_returns_no_changes():
    with _run(raises=True):
        assert collect_docker_diff("x") == []


def test_a_nonzero_return_code_returns_no_changes():
    with _run(returncode=1):
        assert collect_docker_diff("x") == []


def test_real_plain_text_lines_are_parsed():
    with _run(stdout=RAW_DIFF_OUTPUT):
        changes = collect_docker_diff("arrstack-gluetun-1")

    assert changes == [
        {"kind": "C", "path": "/etc/hosts"},
        {"kind": "A", "path": "/gluetun/wg0.conf"},
        {"kind": "A", "path": "/run/nginx.pid"},
        {"kind": "D", "path": "/var/log/old_file"},
    ]


def test_blank_lines_are_skipped():
    with _run(stdout="\nC /etc/hosts\n\n"):
        assert collect_docker_diff("x") == [{"kind": "C", "path": "/etc/hosts"}]


def test_an_unrecognised_kind_letter_is_skipped():
    with _run(stdout="C /etc/hosts\nX /weird\n"):
        assert collect_docker_diff("x") == [{"kind": "C", "path": "/etc/hosts"}]


def test_no_changes_at_all_is_a_real_empty_observation():
    with _run(stdout=""):
        assert collect_docker_diff("x") == []


def test_output_is_sorted_by_path_regardless_of_docker_s_own_order():
    """
    Found in production, 2026-09-28, GIGABYTE: `docker diff`'s own
    line order is not stable across repeated calls against the same
    container even when the underlying set of changes is identical —
    a real diagnostic against the recorded history found 30 of 32
    multi-snapshot subjects holding the exact same set, merely
    re-ordered, on every poll. Sorted at the source so the same real
    set always parses to the same list, whatever order Docker itself
    happened to report it in this time.
    """
    reordered = "D /var/log/old_file\nA /run/nginx.pid\nC /etc/hosts\n"
    with _run(stdout=reordered):
        changes = collect_docker_diff("x")

    assert changes == [
        {"kind": "C", "path": "/etc/hosts"},
        {"kind": "A", "path": "/run/nginx.pid"},
        {"kind": "D", "path": "/var/log/old_file"},
    ]


def test_two_calls_with_the_same_set_in_different_order_parse_identically():
    first_order = "A /run/nginx.pid\nC /etc/hosts\n"
    second_order = "C /etc/hosts\nA /run/nginx.pid\n"

    with _run(stdout=first_order):
        first = collect_docker_diff("x")
    with _run(stdout=second_order):
        second = collect_docker_diff("x")

    assert first == second


def test_the_container_name_is_passed_through():
    with _run(stdout="") as mocked:
        collect_docker_diff("arrstack-gluetun-1")

    assert mocked.call_args[0][0] == ["docker", "diff", "arrstack-gluetun-1"]


# --- collect_running_container_diffs -------------------------------------


def test_no_running_containers_produces_no_diffs():
    with patch("subprocess.run") as mocked:
        mocked.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )
        assert collect_running_container_diffs() == []


def test_a_running_container_s_diff_is_collected_under_its_stable_subject():
    def _fake_run(args, **kwargs):
        if args[:2] == ["docker", "ps"]:
            return subprocess.CompletedProcess(
                args=args, returncode=0, stdout="arrstack-gluetun-1\n", stderr=""
            )
        if args[:2] == ["docker", "inspect"]:
            return subprocess.CompletedProcess(
                args=args, returncode=0, stdout=json.dumps([INSPECT_ENTRY]), stderr=""
            )
        if args[:2] == ["docker", "diff"]:
            return subprocess.CompletedProcess(
                args=args, returncode=0, stdout=RAW_DIFF_OUTPUT, stderr=""
            )
        raise AssertionError(f"unexpected call: {args}")

    with patch("subprocess.run", side_effect=_fake_run):
        results = collect_running_container_diffs()

    assert len(results) == 1
    assert results[0]["subject"] == "arrstack/gluetun"


def test_paths_under_a_declared_mount_are_filtered_out():
    """
    Cadrage decision 2, 2026-09-28: `docker diff`'s own volume
    exclusion is not reliable (a real `moby/moby` bug), so this
    collector filters explicitly against each container's own
    `docker inspect`-reported mount destinations. `INSPECT_ENTRY`
    declares `/gluetun` as a mount; `RAW_DIFF_OUTPUT` reports a change
    under it (`/gluetun/wg0.conf`) alongside three paths that are not
    under any declared mount.
    """

    def _fake_run(args, **kwargs):
        if args[:2] == ["docker", "ps"]:
            return subprocess.CompletedProcess(
                args=args, returncode=0, stdout="arrstack-gluetun-1\n", stderr=""
            )
        if args[:2] == ["docker", "inspect"]:
            return subprocess.CompletedProcess(
                args=args, returncode=0, stdout=json.dumps([INSPECT_ENTRY]), stderr=""
            )
        if args[:2] == ["docker", "diff"]:
            return subprocess.CompletedProcess(
                args=args, returncode=0, stdout=RAW_DIFF_OUTPUT, stderr=""
            )
        raise AssertionError(f"unexpected call: {args}")

    with patch("subprocess.run", side_effect=_fake_run):
        results = collect_running_container_diffs()

    paths = [change["path"] for change in results[0]["changes"]]
    assert "/gluetun/wg0.conf" not in paths
    assert paths == ["/etc/hosts", "/run/nginx.pid", "/var/log/old_file"]


def test_a_mount_at_the_root_itself_is_also_filtered_not_just_its_children():
    entry = dict(INSPECT_ENTRY, Mounts=[{"Destination": "/etc/hosts"}])

    def _fake_run(args, **kwargs):
        if args[:2] == ["docker", "ps"]:
            return subprocess.CompletedProcess(
                args=args, returncode=0, stdout="arrstack-gluetun-1\n", stderr=""
            )
        if args[:2] == ["docker", "inspect"]:
            return subprocess.CompletedProcess(
                args=args, returncode=0, stdout=json.dumps([entry]), stderr=""
            )
        if args[:2] == ["docker", "diff"]:
            return subprocess.CompletedProcess(
                args=args, returncode=0, stdout="C /etc/hosts\n", stderr=""
            )
        raise AssertionError(f"unexpected call: {args}")

    with patch("subprocess.run", side_effect=_fake_run):
        results = collect_running_container_diffs()

    assert results[0]["changes"] == []


def test_a_path_merely_sharing_a_mount_s_prefix_is_not_filtered():
    """The same boundary discipline
    `aistack.timemachine.projection.filter.is_user_data_path` already
    holds: `/gluetunX` must not be treated as under `/gluetun`."""
    entry = dict(INSPECT_ENTRY, Mounts=[{"Destination": "/gluetun"}])

    def _fake_run(args, **kwargs):
        if args[:2] == ["docker", "ps"]:
            return subprocess.CompletedProcess(
                args=args, returncode=0, stdout="arrstack-gluetun-1\n", stderr=""
            )
        if args[:2] == ["docker", "inspect"]:
            return subprocess.CompletedProcess(
                args=args, returncode=0, stdout=json.dumps([entry]), stderr=""
            )
        if args[:2] == ["docker", "diff"]:
            return subprocess.CompletedProcess(
                args=args, returncode=0, stdout="A /gluetunX/file\n", stderr=""
            )
        raise AssertionError(f"unexpected call: {args}")

    with patch("subprocess.run", side_effect=_fake_run):
        results = collect_running_container_diffs()

    assert results[0]["changes"] == [{"kind": "A", "path": "/gluetunX/file"}]
