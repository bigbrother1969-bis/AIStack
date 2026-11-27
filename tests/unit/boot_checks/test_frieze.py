from __future__ import annotations

from datetime import datetime, timedelta, timezone

from aistack.boot_checks.frieze import (
    Moment,
    before,
    declaration_moments,
    docker_moments,
    host_moments,
    journal_moments,
    start_moment,
)
from aistack.boot_checks.history import Event

T0 = datetime(2026, 11, 26, 12, 0, tzinfo=timezone.utc)


def _die(name: str, code: str, at: datetime) -> dict:
    return {"action": "die", "subject": name, "occurred_at": at.isoformat(), "raw": {"Actor": {"Attributes": {"exitCode": code, "name": name}}}}


def test_docker_keeps_only_failures_and_dedupes() -> None:
    events = [
        _die("web", "137", T0),
        _die("web", "137", T0 + timedelta(seconds=10)),
        _die("job", "0", T0),
        {"action": "exec_start", "subject": "web", "occurred_at": T0.isoformat()},
        {"action": "health_status: unhealthy", "subject": "db", "occurred_at": T0.isoformat()},
    ]
    kinds = [(m.kind, m.subject) for m in docker_moments(events)]

    assert kinds == [("died", "web"), ("unhealthy", "db")]


def test_window_order_limit_and_counts() -> None:
    moments = [Moment(T0 - timedelta(minutes=i), "died", f"c{i}", "1") for i in range(1, 5)]
    moments += [Moment(T0 - timedelta(hours=7), "died", "old", "1"), Moment(T0 + timedelta(minutes=1), "died", "later", "1")]
    moments += [Moment(T0 - timedelta(minutes=20), "packages", "host"), Moment(T0 - timedelta(minutes=19), "packages", "host")]
    lines = before(T0, moments, 6, 3)

    assert lines[0] == "2 earlier event(s) not shown"
    assert len(lines) == 4
    assert all("old" not in line and "later" not in line for line in lines)
    assert any("2 package change(s)" in line for line in before(T0, moments, 6, 20))


def test_empty_is_empty() -> None:
    assert before(T0, [], 6, 8) == ()


def test_host_declaration_start_and_journal() -> None:
    hosts = host_moments([("m", [{"at": T0.isoformat(), "kind": "package"}, {"at": T0.isoformat(), "kind": "unit", "unit": "x.service"}])])
    declared = declaration_moments([{"at": T0.isoformat(), "path": "config/boot_checks.yml"}])
    journal = [Event(T0.isoformat(), "disks", "warning", "s", {}, "b"), Event(T0.isoformat(), "services", "ok", "s", {}, "b"), Event(T0.isoformat(), "recurrence", "warning", "s", {}, "b")]

    assert [m.kind for m in hosts] == ["packages", "unit"]
    assert declared[0].subject == "boot_checks.yml"
    assert [m.subject for m in journal_moments(journal, skip="x")] == ["disks"]
    assert start_moment(T0, False)[0].kind == "started_unclean"
    assert start_moment(None, True) == []
