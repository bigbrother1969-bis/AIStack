"""What the vigil tells Gotify about the start-up checks: one summary a day (ADR-0032, B6)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from aistack.boot_checks.controls import Result
from aistack.boot_checks.definition import BootChecksDefinition
from aistack.boot_checks.state import Incident, Verdict, write_verdict
from aistack.i18n import translator_for
from aistack.vigil import boot_notify, notify

T = translator_for("fr")
# 09:00 in Paris (08:00 UTC in November): after the summary hour; 06:30 UTC+1 is before.
MORNING = datetime(2026, 11, 26, 8, 0, tzinfo=timezone.utc)
EARLY = datetime(2026, 11, 26, 5, 30, tzinfo=timezone.utc)
STARTED = MORNING - timedelta(hours=5, minutes=12)
ZONE = "Europe/Paris"
DEFINITION = BootChecksDefinition()


def verdict(overall: str = "ok", results: tuple[Result, ...] = (), incidents: tuple[Incident, ...] = (), checked: datetime = MORNING) -> Verdict:
    anomalies = sum(1 for result in results if result.status in ("warning", "critical"))

    return Verdict(overall, anomalies, checked.isoformat(), "boot-1", STARTED.isoformat(), results, incidents)


def run(tmp_path: Path, previous: notify.State | None = None, now: datetime = MORNING, definition: BootChecksDefinition = DEFINITION):
    return boot_notify.events(T, previous or notify.State(known=True), tmp_path, definition, now, ZONE)


def lines(found: list[notify.Event]) -> list[str]:
    return [event.line for event in found]


def test_nothing_is_told_before_the_hour_and_the_day_is_not_taken(tmp_path: Path) -> None:
    write_verdict(tmp_path, verdict())
    found, day = run(tmp_path, now=EARLY)

    assert found == [] and day == ""


def test_all_well_is_one_short_summary_with_how_long_since_the_start(tmp_path: Path) -> None:
    write_verdict(tmp_path, verdict())
    found, day = run(tmp_path)

    assert lines(found)[0] == "Contrôles du matin :"
    assert "tout va bien depuis 5 h 12" in lines(found)[1] and len(found) == 2
    assert day == "2026-11-26" and not any(event.urgent for event in found)


def test_it_is_told_once_a_day_then_again_the_next_day(tmp_path: Path) -> None:
    write_verdict(tmp_path, verdict())

    assert run(tmp_path, notify.State(known=True, boot_summary_day="2026-11-26"))[0] == []
    assert run(tmp_path, notify.State(known=True, boot_summary_day="2026-11-25"))[1] == "2026-11-26"


def test_a_summary_turned_off_in_the_declaration_says_nothing(tmp_path: Path) -> None:
    write_verdict(tmp_path, verdict())

    assert run(tmp_path, definition=BootChecksDefinition(summary_enabled=False))[0] == []


def test_the_controls_to_watch_and_what_was_resolved_are_named(tmp_path: Path) -> None:
    results = (
        Result("monitor", "warning", "2 down (Gitea, Frigate)"),
        Result("mounts", "ok", "11 declared mount(s) present"),
    )
    incident = Incident("containers", "warning", "2026-11-26T06:10:00+00:00", "1 expected container absent", "2026-11-26T06:25:00+00:00")
    write_verdict(tmp_path, verdict("warning", results, (incident,)))
    found = lines(run(tmp_path)[0])

    assert "  à voir — Sondes Uptime Kuma : 2 down (Gitea, Frigate)" in found
    assert "  résolu depuis le démarrage — Conteneurs présents : 1 expected container absent" in found
    assert not any("Montages" in line for line in found)


def test_each_machine_has_its_line_and_a_critical_one_rings(tmp_path: Path) -> None:
    write_verdict(tmp_path, verdict())
    write_verdict(tmp_path, verdict("critical", (Result("reachable", "critical", "no facts since 07:00"),)), "raspberry")
    found, _ = run(tmp_path)

    assert any("raspberry" in line for line in lines(found))
    assert all(event.urgent for event in found)


def test_an_old_verdict_is_told_as_not_judged_never_as_all_well(tmp_path: Path) -> None:
    write_verdict(tmp_path, verdict(checked=MORNING - timedelta(hours=3)))
    found, _ = run(tmp_path)

    assert not any("tout va bien" in line for line in lines(found))


def test_at_most_three_of_each_are_shown(tmp_path: Path) -> None:
    results = tuple(Result(name, "warning", f"{name} is not right") for name in ("mounts", "probes", "ups", "storage", "backup"))
    write_verdict(tmp_path, verdict("warning", results))

    assert sum(1 for line in lines(run(tmp_path)[0]) if "à voir" in line) == 3


def test_without_a_verdict_nothing_is_said_and_a_fresh_install_only_notes_the_day(tmp_path: Path) -> None:
    assert run(tmp_path) == ([], "")

    write_verdict(tmp_path, verdict())

    assert run(tmp_path, notify.State()) == ([], "2026-11-26")


def test_the_state_keeps_the_day_of_the_summary(tmp_path: Path) -> None:
    notify.write_state(tmp_path, notify.State(known=True, boot_summary_day="2026-11-26"))

    assert notify.read_state(tmp_path).boot_summary_day == "2026-11-26"


# -- in the vigil's pass --------------------------------------------------------------------------


class Recorder(notify.Gotify):
    sent: list[notify.Message]

    def send(self, message, click="", post=None):  # type: ignore[no-untyped-def,override]
        self.sent.append(message)


def _at(monkeypatch, moment: datetime) -> None:  # type: ignore[no-untyped-def]
    from aistack.cli import vigil

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):  # type: ignore[no-untyped-def]
            return moment.astimezone(tz) if tz else moment

    monkeypatch.setattr(vigil, "datetime", Clock)


def test_the_pass_sends_the_summary_once_and_remembers_the_day(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from aistack.cli import vigil

    _at(monkeypatch, MORNING)
    write_verdict(tmp_path, verdict())
    notify.write_state(tmp_path, notify.State(known=True))
    recorder = Recorder("https://g", "t")
    recorder.sent = []

    vigil.one_pass(tmp_path, recorder, dry_run=False, render=False)
    vigil.one_pass(tmp_path, recorder, dry_run=False, render=False)

    assert len(recorder.sent) == 1 and "Contrôles du matin" in recorder.sent[0].body
    assert notify.read_state(tmp_path).boot_summary_day == "2026-11-26"


def test_a_dry_run_keeps_no_day_and_a_gotify_that_does_not_answer_tells_again(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from aistack.cli import vigil

    class Down(notify.Gotify):
        def send(self, message, click="", post=None):  # type: ignore[no-untyped-def,override]
            raise OSError("refused")

    _at(monkeypatch, MORNING)
    write_verdict(tmp_path, verdict())
    notify.write_state(tmp_path, notify.State(known=True))
    vigil.one_pass(tmp_path, None, dry_run=True, render=False)

    assert notify.read_state(tmp_path).boot_summary_day == ""

    assert vigil.one_pass(tmp_path, Down("https://g", "t"), dry_run=False, render=False) == 1
    recorder = Recorder("https://g", "t")
    recorder.sent = []
    vigil.one_pass(tmp_path, recorder, dry_run=False, render=False)

    assert len(recorder.sent) == 1


def test_a_boot_checks_declaration_that_cannot_be_read_does_not_stop_the_vigil(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from aistack.cli import vigil

    broken = tmp_path / "broken.yml"
    broken.write_text("summary: [not, a, mapping", encoding="utf-8")
    monkeypatch.setattr(vigil, "BOOT_CHECKS", broken)
    _at(monkeypatch, MORNING)
    write_verdict(tmp_path, verdict())
    notify.write_state(tmp_path, notify.State(known=True))

    assert vigil.one_pass(tmp_path, None, dry_run=False, render=False) == 0
