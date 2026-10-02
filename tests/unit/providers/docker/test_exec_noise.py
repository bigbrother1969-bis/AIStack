from __future__ import annotations

import json
import subprocess
from unittest.mock import patch

from aistack.providers.docker.events import ExecNoiseFilter, healthcheck_commands_of
from aistack.providers.docker.packages import APK_DB_COMMAND, DPKG_QUERY_COMMAND


def _exec_event(action: str, *, exec_id: str = "e1", container_id: str = "c1") -> dict:
    return {
        "Type": "container",
        "Action": action,
        "Actor": {"ID": container_id, "Attributes": {"execID": exec_id, "name": "x"}},
    }


def _inspect(entries: list[dict] | None, returncode: int = 0):
    def _fake_run(args, **kwargs):
        assert args[:2] == ["docker", "inspect"], args
        return subprocess.CompletedProcess(
            args=args,
            returncode=returncode,
            stdout=json.dumps(entries if entries is not None else []),
            stderr="",
        )

    return patch("subprocess.run", side_effect=_fake_run)


def _no_docker_call():
    def _fake_run(args, **kwargs):
        raise AssertionError(f"unexpected call: {args}")

    return patch("subprocess.run", side_effect=_fake_run)


SHELL_HEALTHCHECK = {"Config": {"Healthcheck": {"Test": ["CMD-SHELL", "/healthcheck.sh"]}}}


# --- healthcheck_commands_of ----------------------------------------------


def test_cmd_shell_runs_through_the_default_shell():
    assert healthcheck_commands_of(SHELL_HEALTHCHECK) == frozenset({"/bin/sh -c /healthcheck.sh"})


def test_cmd_shell_honours_a_declared_shell():
    entry = {
        "Config": {
            "Shell": ["/bin/bash", "-c"],
            "Healthcheck": {"Test": ["CMD-SHELL", "curl -f localhost"]},
        }
    }
    assert healthcheck_commands_of(entry) == frozenset({"/bin/bash -c curl -f localhost"})


def test_cmd_form_is_its_arguments_joined():
    entry = {
        "Config": {
            "Healthcheck": {"Test": ["CMD", "healthcheck.sh", "--connect", "--innodb_initialized"]}
        }
    }
    assert healthcheck_commands_of(entry) == frozenset(
        {"healthcheck.sh --connect --innodb_initialized"}
    )


def test_no_healthcheck_or_none_yields_nothing():
    assert healthcheck_commands_of({"Config": {}}) == frozenset()
    assert healthcheck_commands_of({"Config": {"Healthcheck": {"Test": ["NONE"]}}}) == frozenset()


# --- ExecNoiseFilter ------------------------------------------------------


def test_a_non_exec_event_is_kept_without_asking_docker_anything():
    with _no_docker_call():
        assert ExecNoiseFilter().keep({"Action": "start", "Actor": {"ID": "c1"}})


def test_aistack_s_own_dpkg_probe_is_dropped_with_its_start_and_die():
    command = " ".join(DPKG_QUERY_COMMAND)
    noise = ExecNoiseFilter()

    with _no_docker_call():
        assert not noise.keep(_exec_event(f"exec_create: {command}"))
        assert not noise.keep(_exec_event(f"exec_start: {command}"))
        assert not noise.keep(_exec_event("exec_die"))


def test_aistack_s_own_apk_probe_is_dropped():
    command = " ".join(APK_DB_COMMAND)
    with _no_docker_call():
        assert not ExecNoiseFilter().keep(_exec_event(f"exec_create: {command}"))


def test_a_declared_healthcheck_is_dropped_and_its_container_inspected_once():
    noise = ExecNoiseFilter()

    with _inspect([SHELL_HEALTHCHECK]) as mocked:
        assert not noise.keep(_exec_event("exec_create: /bin/sh -c /healthcheck.sh", exec_id="h1"))
        assert not noise.keep(_exec_event("exec_start: /bin/sh -c /healthcheck.sh", exec_id="h1"))
        assert not noise.keep(_exec_event("exec_die", exec_id="h1"))
        assert not noise.keep(_exec_event("exec_create: /bin/sh -c /healthcheck.sh", exec_id="h2"))

    assert mocked.call_count == 1


def test_a_human_exec_is_kept_with_its_die():
    noise = ExecNoiseFilter()

    with _inspect([SHELL_HEALTHCHECK]):
        assert noise.keep(_exec_event("exec_create: bash", exec_id="u1"))
        assert noise.keep(_exec_event("exec_start: bash", exec_id="u1"))
        assert noise.keep(_exec_event("exec_die", exec_id="u1"))


def test_an_exec_on_a_container_docker_cannot_inspect_is_kept_and_not_cached():
    noise = ExecNoiseFilter()

    with _inspect(None, returncode=1):
        assert noise.keep(_exec_event("exec_create: /bin/sh -c /healthcheck.sh"))

    with _inspect([SHELL_HEALTHCHECK]):
        assert not noise.keep(_exec_event("exec_create: /bin/sh -c /healthcheck.sh"))


def test_an_exec_die_never_seen_created_is_kept():
    with _no_docker_call():
        assert ExecNoiseFilter().keep(_exec_event("exec_die", exec_id="unknown"))
