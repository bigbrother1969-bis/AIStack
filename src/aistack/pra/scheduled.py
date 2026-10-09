"""
Scheduled restore tests (2.0, tranche 2; the owner, 2026-10-09: "tests
PRA planifiés", and, for the record, "enregistrée seule").

Every week, `aistack-pra.timer` restores each service that has a
sandbox recipe (`ADR-0018`), with the newest backup, in the sandbox —
never touching the live service. Each outcome is recorded here, by
AIStack, in the data directory: `pra/scheduled.jsonl`, one line per
run, appended, never rewritten.

`pra_tests.yml` stays the owner's hand-written file, comments
included: AIStack never rewrites it. The Tests PRA domain reads both
and keeps, per service, the more recent outcome — so a scheduled
success refreshes a service's date, and a scheduled failure is the
newest word on it until a later run succeeds.
"""

from __future__ import annotations

import fcntl
import json
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

from aistack.contracts.pra_test_reading import FAILED, SUCCESS, PraTestReading

RECORDS = Path("pra") / "scheduled.jsonl"
GENERATED_DIR = Path("reports/generated")
# A service tested by the schedule less than this long ago is not
# tested again by a run without `--all`: the weekly timer, caught up
# after a host was off (`Persistent=true`), never tests twice a week.
EVERY = timedelta(days=6)


@dataclass(frozen=True)
class ScheduledTest:
    service: str
    at: datetime
    status: str
    run_id: str = ""
    rto_minutes: int | None = None
    failure: str = ""

    def as_json(self) -> str:
        return json.dumps(
            {
                "service": self.service,
                "at": self.at.isoformat(timespec="seconds"),
                "status": self.status,
                "run_id": self.run_id,
                "rto_minutes": self.rto_minutes,
                "failure": self.failure,
            },
            ensure_ascii=False,
        )


def record(generated_dir: Path, test: ScheduledTest) -> Path:
    path = generated_dir / RECORDS
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(test.as_json() + "\n")
    return path


def read_records(generated_dir: Path) -> list[ScheduledTest]:
    path = generated_dir / RECORDS
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    found = []
    for line in lines:
        try:
            raw = json.loads(line)
            at = datetime.fromisoformat(str(raw["at"]))
            status = str(raw["status"])
            if status not in (SUCCESS, FAILED):
                continue
            rto = raw.get("rto_minutes")
            found.append(
                ScheduledTest(
                    service=str(raw["service"]),
                    at=at if at.tzinfo else at.replace(tzinfo=timezone.utc),
                    status=status,
                    run_id=str(raw.get("run_id") or ""),
                    rto_minutes=int(rto) if rto is not None else None,
                    failure=str(raw.get("failure") or ""),
                )
            )
        except (ValueError, KeyError, TypeError):
            continue
    return found


def latest(records: Sequence[ScheduledTest]) -> dict[str, ScheduledTest]:
    newest: dict[str, ScheduledTest] = {}
    for test in records:
        if test.service not in newest or test.at >= newest[test.service].at:
            newest[test.service] = test
    return newest


def with_scheduled(
    readings: Sequence[PraTestReading], generated_dir: Path = GENERATED_DIR
) -> tuple[PraTestReading, ...]:
    """
    `pra_tests.yml`'s readings, each replaced by the service's latest
    scheduled outcome when that one is more recent. A service the
    schedule tests but the file does not name is added.
    """

    newest = latest(read_records(generated_dir))
    if not newest:
        return tuple(readings)
    observed_at = readings[0].observed_at if readings else datetime.now(timezone.utc)
    merged = []
    for reading in readings:
        test = newest.pop(reading.service, None)
        if test is not None and (reading.tested_at is None or test.at >= reading.tested_at):
            reading = replace(
                reading,
                status=test.status,
                tested_at=test.at,
                rto_minutes=test.rto_minutes if test.status == SUCCESS else None,
            )
        merged.append(reading)
    for test in newest.values():
        merged.append(
            PraTestReading(
                service=test.service,
                observed_at=observed_at,
                status=test.status,
                tested_at=test.at,
                rto_minutes=test.rto_minutes if test.status == SUCCESS else None,
            )
        )
    return tuple(merged)


def due(services: Sequence[str], records: Sequence[ScheduledTest], now: datetime) -> list[str]:
    """The services the schedule has not tested within `EVERY`."""

    newest = latest(records)
    return [s for s in services if s not in newest or now - newest[s].at >= EVERY]


@contextmanager
def after_the_dock(generated_dir: Path) -> Iterator[None]:
    """
    Wait for the dock executor's lock (`aistack.dock.executor.exclusive`)
    and hold it: a scheduled restore never runs beside a dock change,
    and the dock, which never waits, skips its two-minute turn while a
    restore runs.
    """

    path = generated_dir / "dock" / "executor.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)
