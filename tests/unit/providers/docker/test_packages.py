from __future__ import annotations

import json
import subprocess
from unittest.mock import patch

from aistack.providers.docker.packages import (
    collect_package_inventory,
    collect_running_container_packages,
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
    "Mounts": [],
}

DPKG_STDOUT = "curl\t7.88.1-10\nbash\t5.2.15-2+b7\n"

APK_INSTALLED = (
    "P:musl\n"
    "V:1.2.4-r2\n"
    "A:x86_64\n"
    "\n"
    "P:busybox\n"
    "V:1.36.1-r15\n"
    "\n"
)


def _run(*, ps_stdout: str = "", inspect_stdout: str = "[]", exec_handler=None):
    def _fake_run(args, **kwargs):
        if args[:2] == ["docker", "ps"]:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout=ps_stdout, stderr="")
        if args[:2] == ["docker", "inspect"]:
            return subprocess.CompletedProcess(
                args=args, returncode=0, stdout=inspect_stdout, stderr=""
            )
        if args[:2] == ["docker", "exec"] and exec_handler is not None:
            return exec_handler(args)
        raise AssertionError(f"unexpected call: {args}")

    return patch("subprocess.run", side_effect=_fake_run)


def _always_fails(args):
    return subprocess.CompletedProcess(args=args, returncode=1, stdout="", stderr="")


# --- collect_package_inventory --------------------------------------------


def test_dpkg_is_tried_first_and_its_packages_are_parsed_and_sorted():
    def exec_handler(args):
        assert args[3] == "dpkg-query"
        return subprocess.CompletedProcess(args=args, returncode=0, stdout=DPKG_STDOUT, stderr="")

    with _run(exec_handler=exec_handler):
        result = collect_package_inventory("frigate")

    assert result == {
        "mechanism": "dpkg",
        "packages": [
            {"name": "bash", "version": "5.2.15-2+b7"},
            {"name": "curl", "version": "7.88.1-10"},
        ],
    }


def test_a_dpkg_failure_falls_back_to_apk():
    def exec_handler(args):
        if args[3] == "dpkg-query":
            return _always_fails(args)
        assert args[3] == "cat"
        assert args[4] == "/lib/apk/db/installed"
        return subprocess.CompletedProcess(args=args, returncode=0, stdout=APK_INSTALLED, stderr="")

    with _run(exec_handler=exec_handler):
        result = collect_package_inventory("frigate")

    assert result == {
        "mechanism": "apk",
        "packages": [
            {"name": "busybox", "version": "1.36.1-r15"},
            {"name": "musl", "version": "1.2.4-r2"},
        ],
    }


def test_neither_mechanism_answering_yields_none_with_an_empty_list():
    with _run(exec_handler=_always_fails):
        result = collect_package_inventory("frigate")

    assert result == {"mechanism": "none", "packages": []}


def test_a_dpkg_record_missing_the_version_separator_is_skipped():
    def exec_handler(args):
        return subprocess.CompletedProcess(
            args=args, returncode=0, stdout="curl\t1.0\nmalformed-line\n", stderr=""
        )

    with _run(exec_handler=exec_handler):
        result = collect_package_inventory("frigate")

    assert result == {"mechanism": "dpkg", "packages": [{"name": "curl", "version": "1.0"}]}


def test_an_apk_record_missing_its_version_is_skipped():
    def exec_handler(args):
        if args[3] == "dpkg-query":
            return _always_fails(args)
        return subprocess.CompletedProcess(
            args=args, returncode=0, stdout="P:no-version\n\nP:musl\nV:1.2.4-r2\n\n", stderr=""
        )

    with _run(exec_handler=exec_handler):
        result = collect_package_inventory("frigate")

    assert result == {"mechanism": "apk", "packages": [{"name": "musl", "version": "1.2.4-r2"}]}


def test_an_empty_dpkg_answer_is_a_real_empty_inventory_not_a_fallback():
    def exec_handler(args):
        assert args[3] == "dpkg-query"
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    with _run(exec_handler=exec_handler):
        result = collect_package_inventory("frigate")

    assert result == {"mechanism": "dpkg", "packages": []}


# --- collect_running_container_packages -----------------------------------


def test_no_running_containers_produces_no_inventories():
    with _run(inspect_stdout="[]"):
        assert collect_running_container_packages() == []


def test_a_running_container_s_inventory_is_collected_under_its_stable_subject():
    def exec_handler(args):
        return subprocess.CompletedProcess(args=args, returncode=0, stdout=DPKG_STDOUT, stderr="")

    with _run(
        ps_stdout="arrstack-gluetun-1\n",
        inspect_stdout=json.dumps([INSPECT_ENTRY]),
        exec_handler=exec_handler,
    ):
        results = collect_running_container_packages()

    assert results == [
        {
            "subject": "arrstack/gluetun",
            "mechanism": "dpkg",
            "packages": [
                {"name": "bash", "version": "5.2.15-2+b7"},
                {"name": "curl", "version": "7.88.1-10"},
            ],
        }
    ]


def test_two_running_containers_each_get_their_own_entry():
    second_entry = dict(INSPECT_ENTRY, Name="/frigate", Config={"Labels": {}})

    with _run(
        ps_stdout="arrstack-gluetun-1\nfrigate\n",
        inspect_stdout=json.dumps([INSPECT_ENTRY, second_entry]),
        exec_handler=_always_fails,
    ):
        results = collect_running_container_packages()

    assert results == [
        {"subject": "arrstack/gluetun", "mechanism": "none", "packages": []},
        {"subject": "frigate", "mechanism": "none", "packages": []},
    ]
