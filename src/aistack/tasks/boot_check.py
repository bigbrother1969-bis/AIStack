from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from aistack.boot_checks.controls import Reading, evaluate
from aistack.boot_checks.facts import read_facts_file
from aistack.boot_checks.load import load_boot_checks_yaml
from aistack.boot_checks.report import EXIT, describe, suggestion
from aistack.boot_checks.state import judge, read_verdict, unknown, write_verdict
from aistack.config import PACKAGE_ROOT, configured
from aistack.kernel.execution import Observation, ObservationContext, Request

DEFAULT_GENERATED_DIR = "reports/generated"
# Where the host unit aistack-boot-facts writes, under the data directory.
HOST_DIR = "boot-host"

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

        if payload.get("suggest"):
            if facts is not None:
                data.update(text=suggestion(facts), exit_code=0)
        else:
            if facts is None:
                verdict = unknown(now, note)
            else:
                definition = load_boot_checks_yaml(Path(payload.get("definition", DEFAULT_DEFINITION)))
                storage, backup = cockpit_readings(_hostname()) if payload.get("cockpit", True) else (None, None)
                verdict = judge(evaluate(facts, definition, now, storage, backup), facts, now, read_verdict(generated_dir))

            if not payload.get("dry_run"):
                write_verdict(generated_dir, verdict)

            data = {
                "overall": verdict.overall,
                "anomalies": verdict.anomalies,
                "text": describe(verdict),
                "exit_code": EXIT[verdict.overall],
                "verdict": asdict(verdict),
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


def _hostname() -> str:
    import socket

    return socket.gethostname()
