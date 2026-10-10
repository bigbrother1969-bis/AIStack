from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from typing import Any, Mapping

from aistack.providers.docker.identity import stable_subject_from_labels


# Passive container traceability from `docker events`, polled over
# bounded windows rather than through a live subscription (`ADR-0011`).
# Returns what Docker reported, plus only the three facts derived at
# collection time (`ADR-0011` § 3-4): stable subject, occurrence time and
# action. No interpretation such as "this was an upgrade".


def collect_docker_events(since: str, until: str) -> list[dict[str, Any]]:
    """Every Docker event in `[since, until)`, raw, in one bounded call.

    `since`/`until` are passed to Docker unchanged (RFC 3339 or Unix
    timestamp). Returns `[]` on any failure, so one bad cycle cannot crash
    a long-running monitor (`aistack.cli.docker_events_monitor`).
    """

    try:
        result = subprocess.run(
            [
                "docker",
                "events",
                "--since",
                since,
                "--until",
                until,
                "--format",
                "{{json .}}",
            ],
            capture_output=True,
            text=True,
        )
    except OSError:
        return []

    if result.returncode != 0:
        return []

    events: list[dict[str, Any]] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            events.append(payload)

    return events


def stable_subject_of(event: Mapping[str, Any]) -> str:
    """Stable subject of one raw Docker event (`ADR-0011` § Decision 3).

    Extracts the actor's labels, name and id and applies
    `stable_subject_from_labels`. The container id is only the last
    resort, since recreation changes it.
    """

    actor = event.get("Actor")
    attributes = actor.get("Attributes") if isinstance(actor, dict) else None
    attributes = attributes if isinstance(attributes, dict) else {}
    actor_id = actor.get("ID") if isinstance(actor, dict) else None

    return stable_subject_from_labels(
        attributes,
        name=str(attributes.get("name") or ""),
        container_id=str(actor_id or ""),
    )


def occurred_at_of(event: Mapping[str, Any]) -> datetime:
    """When Docker says the event happened (`ADR-0011` § 4
    `aistack:occurredAt`): `timeNano`, else `time`, else now (malformed
    payload)."""

    time_nano = event.get("timeNano")
    if isinstance(time_nano, (int, float)):
        # Integer division: a float cannot hold ~19 digits of nanoseconds
        # and would round the last microsecond wrongly.
        seconds, nanoseconds = divmod(int(time_nano), 1_000_000_000)
        return datetime.fromtimestamp(seconds, tz=timezone.utc).replace(
            microsecond=nanoseconds // 1000
        )

    time_seconds = event.get("time")
    if isinstance(time_seconds, (int, float)):
        return datetime.fromtimestamp(time_seconds, tz=timezone.utc)

    return datetime.now(timezone.utc)


def docker_action_of(event: Mapping[str, Any]) -> str:
    """The action Docker recorded (`"start"`, `"destroy"`, `"exec_create"`, ...), or `""` when absent."""

    action = event.get("Action")
    return str(action) if action else ""


def enrich(event: Mapping[str, Any]) -> dict[str, Any]:
    """One raw Docker event with `subject`, `occurred_at` and `action`
    (`ADR-0011` § 3-4) added beside the unchanged `raw` payload."""

    return {
        "subject": stable_subject_of(event),
        "occurred_at": occurred_at_of(event).isoformat(),
        "action": docker_action_of(event),
        "raw": dict(event),
    }


# --- Exec noise: AIStack's own probes and declared healthchecks ------------
#
# Healthcheck runs and AIStack's own package probes make up most `exec_*`
# events and bury real faults. Only those two automatic kinds are
# dropped; any other `docker exec` (e.g. by a person) is kept.

_MAX_REMEMBERED_EXEC_IDS = 4096
_MAX_CACHED_CONTAINERS = 1024


def _aistack_probe_commands() -> frozenset[str]:
    # Read from `packages` rather than copied, so the two cannot drift.
    from aistack.providers.docker.packages import APK_DB_COMMAND, DPKG_QUERY_COMMAND

    return frozenset(
        " ".join(command).strip() for command in (DPKG_QUERY_COMMAND, APK_DB_COMMAND)
    )


def healthcheck_commands_of(inspect_entry: Mapping[str, Any]) -> frozenset[str]:
    """The command line(s) Docker shows after `exec_create: ` /
    `exec_start: ` when it runs this container's declared healthcheck.

    `CMD-SHELL x` appears as `<Config.Shell or /bin/sh -c> x`; `CMD a b`
    as `a b`. `NONE` or no healthcheck yields nothing.
    """

    config = inspect_entry.get("Config")
    config = config if isinstance(config, dict) else {}
    healthcheck = config.get("Healthcheck")
    test = healthcheck.get("Test") if isinstance(healthcheck, dict) else None
    if not isinstance(test, list) or len(test) < 2:
        return frozenset()

    kind, rest = str(test[0]), [str(part) for part in test[1:]]
    if kind == "CMD-SHELL":
        shell = config.get("Shell")
        shell_parts = (
            [str(part) for part in shell]
            if isinstance(shell, list) and shell
            else ["/bin/sh", "-c"]
        )
        return frozenset({" ".join([*shell_parts, *rest]).strip()})
    if kind == "CMD":
        return frozenset({" ".join(rest).strip()})
    return frozenset()


def _inspect_healthcheck(container_id: str) -> frozenset[str] | None:
    """`None` when Docker could not say — never cached, never read as "no healthcheck"."""

    from aistack.providers.docker.identity import inspect_containers

    entries = inspect_containers([container_id])
    if not entries or not isinstance(entries[0], dict):
        return None
    return healthcheck_commands_of(entries[0])


class ExecNoiseFilter:
    """Decide whether a raw Docker event is exec noise (an AIStack package
    probe or a declared healthcheck) to leave out of Observation History.

    `exec_die` carries only its `execID`, so the filter remembers the
    `execID`s it dropped (bounded) and drops their `exec_die` too. It must
    live as long as the monitor loop, since `exec_die` can fall in the next
    poll window. When in doubt (uninspectable container, unseen
    `exec_create`), the event is kept.
    """

    def __init__(
        self,
        *,
        healthchecks_by_subject: Mapping[str, frozenset[str]] | None = None,
        remember_uninspectable: bool = False,
    ) -> None:
        """The keyword arguments are for refiltering archived history, not
        the live monitor. `healthchecks_by_subject` stands in for container
        ids that no longer exist; `remember_uninspectable` caches ids Docker
        could not inspect so they are not asked again.
        """

        self._probe_commands = _aistack_probe_commands()
        self._dropped_exec_ids: dict[str, None] = {}
        self._healthchecks: dict[str, frozenset[str]] = {}
        self._healthchecks_by_subject = healthchecks_by_subject or {}
        self._remember_uninspectable = remember_uninspectable

    def _healthcheck_commands(self, container_id: str) -> frozenset[str]:
        cached = self._healthchecks.get(container_id)
        if cached is not None:
            return cached
        commands = _inspect_healthcheck(container_id)
        if commands is None:
            if not self._remember_uninspectable:
                return frozenset()
            commands = frozenset()
        if len(self._healthchecks) >= _MAX_CACHED_CONTAINERS:
            self._healthchecks.clear()
        self._healthchecks[container_id] = commands
        return commands

    def _remember(self, exec_id: str) -> None:
        if not exec_id:
            return
        self._dropped_exec_ids[exec_id] = None
        while len(self._dropped_exec_ids) > _MAX_REMEMBERED_EXEC_IDS:
            self._dropped_exec_ids.pop(next(iter(self._dropped_exec_ids)))

    def keep(self, event: Mapping[str, Any]) -> bool:
        action = docker_action_of(event)
        if not action.startswith("exec_"):
            return True

        actor = event.get("Actor")
        actor = actor if isinstance(actor, dict) else {}
        attributes = actor.get("Attributes")
        attributes = attributes if isinstance(attributes, dict) else {}
        exec_id = str(attributes.get("execID") or "")

        verb, separator, command = action.partition(":")
        if not separator:
            # `exec_die` and the like: no command, only the execID.
            return not (exec_id and exec_id in self._dropped_exec_ids)

        command = command.strip()
        noisy = command in self._probe_commands
        if not noisy:
            container_id = str(actor.get("ID") or "")
            noisy = bool(container_id) and command in self._healthcheck_commands(
                container_id
            )
        if not noisy and self._healthchecks_by_subject:
            noisy = command in self._healthchecks_by_subject.get(
                stable_subject_of(event), frozenset()
            )
        if noisy:
            self._remember(exec_id)
        return not noisy


def current_healthchecks_by_subject() -> dict[str, frozenset[str]]:
    """Declared healthcheck commands of every running container, by stable
    subject (for `ExecNoiseFilter(healthchecks_by_subject=...)`). `{}` when
    Docker cannot be reached."""

    from aistack.providers.docker.identity import (
        inspect_containers,
        list_running_container_names,
    )

    by_subject: dict[str, frozenset[str]] = {}
    for entry in inspect_containers(list_running_container_names()):
        if not isinstance(entry, dict):
            continue
        config = entry.get("Config")
        labels = config.get("Labels") if isinstance(config, dict) else None
        labels = labels if isinstance(labels, dict) else {}
        raw_name = entry.get("Name")
        subject = stable_subject_from_labels(
            labels,
            name=str(raw_name).lstrip("/") if raw_name else "",
            container_id=str(entry.get("Id") or ""),
        )
        commands = healthcheck_commands_of(entry)
        if commands:
            by_subject[subject] = commands
    return by_subject
