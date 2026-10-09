"""Scheduled restore tests (2.0, 2026-10-09)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from aistack.cli import pra_schedule
from aistack.contracts.pra_test_reading import PraTestReading
from aistack.pra.scheduled import ScheduledTest, due, read_records, record, with_scheduled

NOW = datetime(2026, 10, 4, 4, 30, tzinfo=timezone.utc)
OBSERVED = datetime(2026, 10, 9, 12, 0, tzinfo=timezone.utc)


def _reading(service: str, date: str | None) -> PraTestReading:
    if date is None:
        return PraTestReading(service=service, observed_at=OBSERVED)
    return PraTestReading(
        service=service,
        observed_at=OBSERVED,
        status="success",
        tested_at=datetime.fromisoformat(date).replace(tzinfo=timezone.utc),
        rto_minutes=3,
    )


def test_records_are_appended_and_read_back(tmp_path: Path) -> None:
    record(tmp_path, ScheduledTest("wordpress", NOW, "success", "wordpress-1", 1))
    record(tmp_path, ScheduledTest("immich", NOW, "failed", "immich-1", failure="dump not found"))
    (tmp_path / "pra" / "scheduled.jsonl").open("a").write("not json\n")

    tests = read_records(tmp_path)
    assert [(t.service, t.status) for t in tests] == [("wordpress", "success"), ("immich", "failed")]
    assert tests[1].failure == "dump not found"


def test_a_newer_scheduled_outcome_replaces_the_declared_one(tmp_path: Path) -> None:
    record(tmp_path, ScheduledTest("wordpress", NOW, "success", rto_minutes=1))
    record(tmp_path, ScheduledTest("immich", NOW, "failed", failure="x"))
    record(tmp_path, ScheduledTest("vikunja", NOW - timedelta(days=60), "failed", failure="old"))

    merged = {
        r.service: r
        for r in with_scheduled(
            (_reading("wordpress", "2026-10-01"), _reading("immich", "2026-10-01"),
             _reading("vikunja", "2026-09-26"), _reading("gigabyte", None)),
            tmp_path,
        )
    }

    assert merged["wordpress"].tested_at == NOW and merged["wordpress"].rto_minutes == 1
    assert merged["immich"].status == "failed" and merged["immich"].rto_minutes is None
    # Older than what the owner recorded by hand: the hand record stands.
    assert merged["vikunja"].status == "success"
    assert merged["gigabyte"].status is None


def test_a_service_only_the_schedule_tests_is_added(tmp_path: Path) -> None:
    record(tmp_path, ScheduledTest("nextcloud", NOW, "success", rto_minutes=2))
    (only,) = with_scheduled((), tmp_path)
    assert only.service == "nextcloud" and only.status == "success"


def test_nothing_recorded_leaves_the_readings_unchanged(tmp_path: Path) -> None:
    readings = (_reading("wordpress", "2026-10-08"),)
    assert with_scheduled(readings, tmp_path) == readings


def test_due_skips_what_the_schedule_tested_this_week() -> None:
    records = [
        ScheduledTest("wordpress", NOW - timedelta(days=2), "success"),
        ScheduledTest("immich", NOW - timedelta(days=7), "success"),
    ]
    assert due(["immich", "nextcloud", "wordpress"], records, NOW) == ["immich", "nextcloud"]


class _Run:
    def __init__(self, service: str, ok: bool) -> None:
        self.service = service
        self.started_at = NOW
        self.run_id = f"{service}-run"
        self.succeeded = ok
        self.recovery_seconds = 90.0 if ok else None
        self.failure = "" if ok else "no dump newer than 2 days"


class _Declaration:
    recipes = {"wordpress": object(), "immich": object()}


def test_the_command_records_every_outcome(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setattr(pra_schedule, "load_sandbox_declaration", lambda: _Declaration())

    def fake_restore(service, declaration, generated, runner, progress):
        return _Run(service, service == "wordpress"), generated / "sandbox" / f"{service}.json"

    monkeypatch.setattr(pra_schedule, "restore", fake_restore)

    assert pra_schedule.main([], root=tmp_path) == 1
    data = tmp_path / "reports" / "generated"
    tests = {t.service: t for t in read_records(data)}
    assert tests["wordpress"].status == "success" and tests["wordpress"].rto_minutes == 2
    assert tests["immich"].status == "failed" and "no dump" in tests["immich"].failure
    assert (data / "dock" / "executor.lock").exists()

    assert pra_schedule.main(["--list"], root=tmp_path) == 0
    assert "immich       failed" in capsys.readouterr().out
    assert pra_schedule.main(["nextcloud"], root=tmp_path) == 2
    assert "No sandbox recipe for nextcloud" in capsys.readouterr().out
