from __future__ import annotations

import os
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

from aistack.boot_checks.controls import Reading, evaluate, evaluate_companion
from aistack.boot_checks.definition import BootChecksDefinition
from aistack.boot_checks.facts import BootFacts, read_facts_file
from aistack.boot_checks.load import load_boot_checks_yaml
from aistack.boot_checks.monitor import MonitorReading, read_monitors
from aistack.boot_checks.report import EXIT, companion_suggestion, describe, suggestion
from aistack.boot_checks.state import Verdict, judge, judge_silent, read_verdict, unknown, write_verdict
from aistack.api_keys import read_store
from aistack.config import PACKAGE_ROOT, configured
from aistack.hosts.records import TracedHost, load_hosts_declaration
from aistack.kernel.execution import Observation, ObservationContext, Request

DEFAULT_GENERATED_DIR = "reports/generated"
# Where the host unit aistack-boot-facts writes, under the data directory.
HOST_DIR = "boot-host"
# The folder, under a companion's directory of hosts.yml, where its own host unit's facts arrive (ADR-0020's push).
COMPANION_DIR = "boot"

DEFAULT_DEFINITION = configured(PACKAGE_ROOT / "boot_checks" / "definitions" / "boot_checks.yml")


def cockpit_readings(hostname: str) -> tuple[Reading, Reading]:
    """What the health cockpit says of the disks (OPS-0005) and of the backups (OPS-0006) on this host."""

    from aistack.health.domains import backup_domain, storage_domain

    def read(build) -> Reading:  # type: ignore[no-untyped-def]
        try:
            domain = build(hostname)
        except Exception as error:  # a provider may fail in many ways; the control says it was not read
            return Reading(False, 0, f"not read: {type(error).__name__}")

        return Reading(domain.instrumented, len(domain.findings), domain.note)

    return read(storage_domain), read(backup_domain)


class BootCheckTask:
    """
    Judge how the host started (`boot.check`, ADR-0032 slice B2).

    Reads the facts the host unit `aistack-boot-facts` wrote, judges them
    against `boot_checks.yml` (and, unless told not to, what the health
    cockpit says of the disks and the backups) and writes the verdict as
    `boot-check.json`. Read-only on every host: it changes nothing but its
    own verdict. The payload says where the facts and the verdict are
    (`generated_dir`, default `reports/generated`; `facts_dir`, default
    `<generated_dir>/boot-host`), which declaration to read (`definition`),
    and whether to read the cockpit (`cockpit`), write nothing (`dry_run`)
    or only suggest a declaration from the facts (`suggest`).

    Returns an Observation of plain values: the overall status, the
    anomalies, the text to print and the exit code that says how it went.
    """

    task_id = "boot.check"
    task_name = "Start-up checks"

    def execute(self, request: Request) -> Observation:
        payload = request.payload
        generated_dir = Path(payload.get("generated_dir", DEFAULT_GENERATED_DIR))
        facts_dir = Path(payload.get("facts_dir", generated_dir / HOST_DIR))
        now = datetime.now(timezone.utc)
        facts, note = read_facts_file(facts_dir, now)
        data: dict[str, object] = {"overall": "unknown", "anomalies": 0, "text": note, "exit_code": EXIT["unknown"]}

        definition = load_boot_checks_yaml(Path(payload.get("definition", DEFAULT_DEFINITION)))
        companions = _companion_folders(generated_dir, payload.get("hosts")) if definition.companions else []

        if payload.get("suggest"):
            if facts is not None:
                text = suggestion(facts)
                names = _monitors(generated_dir)

                if names is not None and names.reachable:
                    text += "\nexpected_monitors: [" + ", ".join(sorted(names.monitors)) + "]"

                shown = _companion_facts(companions, definition, now)

                if shown:
                    text += "\ncompanion_mounts:\n" + "\n".join(companion_suggestion(name, found) for name, found in shown)

                data.update(text=text, exit_code=0)
        else:
            if facts is None:
                verdict = unknown(now, note)
            else:
                storage, backup = cockpit_readings(_hostname()) if payload.get("cockpit", True) else (None, None)
                monitors = _monitors(generated_dir)
                verdict = judge(evaluate(facts, definition, now, storage, backup, monitors), facts, now, read_verdict(generated_dir))

            if not payload.get("dry_run"):
                write_verdict(generated_dir, verdict)

            others = _judge_companions(companions, definition, now, generated_dir, bool(payload.get("dry_run")))
            status = _worse(verdict.overall, others)
            text = "\n".join([describe(verdict), *(describe(other, name) for name, other in others)])

            data = {
                "overall": status,
                "anomalies": verdict.anomalies + sum(other.anomalies for _, other in others),
                "text": text,
                "exit_code": EXIT[status],
                "verdict": asdict(verdict),
                "companions": {name: asdict(other) for name, other in others},
            }

        return Observation(
            context=ObservationContext(
                request_id=request.request_id,
                component_type="task",
                component_id=self.task_id,
                operation="execute",
            ),
            data=data,
        )


KUMA_URL = "AISTACK_KUMA_URL"
KUMA_KEY = "AISTACK_KUMA_API_KEY"


def _monitors(generated_dir: Path) -> MonitorReading | None:
    """What Uptime Kuma says, when its address and an API key are set (Settings, or the environment); `None` when they are not."""

    stored = read_store(generated_dir)
    url = stored.get(KUMA_URL) or os.environ.get(KUMA_URL, "")
    key = stored.get(KUMA_KEY) or os.environ.get(KUMA_KEY, "")

    if not url or not key:
        return None

    return read_monitors(url, key)


def _companion_folders(generated_dir: Path, hosts_file: object = None) -> list[TracedHost]:
    """The traced hosts that push start-up facts (a `boot` folder); a host with none is not judged."""

    try:
        hosts = load_hosts_declaration(generated_dir, Path(str(hosts_file)) if hosts_file else None).hosts
    except (OSError, ValueError, yaml.YAMLError):
        return []

    return [host for host in hosts if (host.directory / COMPANION_DIR).is_dir()]


def _companion_facts(hosts: list[TracedHost], definition: BootChecksDefinition, now: datetime) -> list[tuple[str, BootFacts]]:
    found = []

    for host in hosts:
        facts, _ = read_facts_file(host.directory / COMPANION_DIR, now, timedelta(minutes=definition.companion_silent_minutes))

        if facts is not None:
            found.append((host.name, facts))

    return found


def _judge_companions(
    hosts: list[TracedHost], definition: BootChecksDefinition, now: datetime, generated_dir: Path, dry_run: bool
) -> list[tuple[str, Verdict]]:
    """Each companion's verdict, in a file of its own; one whose name is not a plain one is left out and said by the log."""

    verdicts = []
    silent = timedelta(minutes=definition.companion_silent_minutes)

    for host in hosts:
        facts, note = read_facts_file(host.directory / COMPANION_DIR, now, silent)
        results = evaluate_companion(host.name, facts, note, definition, now)

        try:
            previous = read_verdict(generated_dir, host.name)
            verdict = (
                judge_silent(results, now, previous) if facts is None else judge(results, facts, now, previous)
            )

            if not dry_run:
                write_verdict(generated_dir, verdict, host.name)
        except ValueError:
            continue

        verdicts.append((host.name, verdict))

    return verdicts


def _worse(status: str, others: list[tuple[str, Verdict]]) -> str:
    """The worst status of the machine and its companions, for the exit code."""

    order = ["ok", "pending", "unknown", "warning", "critical"]
    statuses = [status, *(other.overall for _, other in others)]

    return max(statuses, key=lambda item: order.index(item) if item in order else 0)


def _hostname() -> str:
    import socket

    return socket.gethostname()
