"""What the vigil tells Gotify about security (ADR-0028 T4a)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from aistack.cli import vigil
from aistack.i18n import translator_for
from aistack.security import series, window
from aistack.security.definition import SecurityDefinition
from aistack.vigil import notify, security_notify

T = translator_for("fr")
DEFINITION = SecurityDefinition()
# 09:30 in Paris (08:30 UTC in November): after the digest hour.
MORNING = datetime(2026, 11, 20, 8, 30, tzinfo=timezone.utc)
EARLY = datetime(2026, 11, 20, 5, 30, tzinfo=timezone.utc)  # 06:30 in Paris


def finding(key: str, severity: str, title: str = "un constat", evidence: tuple[str, ...] = ()) -> dict:
    return {"key": key, "severity": severity, "title": title, "evidence": list(evidence), "unknown": ""}


def report(*findings: dict, collected: datetime = MORNING) -> dict:
    return {"collected_at": collected.isoformat(), "findings": list(findings), "measures": {"findings.watch": 1}}


def state(**kept: object) -> notify.State:
    return notify.State(known=True, security_known=True, **kept)  # type: ignore[arg-type]


def run(previous: notify.State, made: dict | None, now: datetime = MORNING, opened=None, expired=None):
    return security_notify.events(T, previous, made, opened, expired, now, DEFINITION)


def lines(outcome: security_notify.Outcome) -> list[str]:
    return [event.line for event in outcome.events]


def test_a_finding_to_fix_is_told_at_once_then_not_again() -> None:
    made = report(finding("hygiene.docker", "fix", "Un conteneur a le socket Docker", ("grafana",)))
    first = run(state(), made)

    assert lines(first) == ["Sécurité, à corriger — Un conteneur a le socket Docker", "· grafana"]
    assert not any(event.urgent for event in first.events)
    assert first.told == ("hygiene.docker",)

    again = run(state(security_told=first.told), made)
    assert again.events == [] and again.told == ("hygiene.docker",)


def test_an_urgent_finding_rings() -> None:
    outcome = run(state(), report(finding("exposure.docker_api", "urgent", "L'API Docker est ouverte")))
    assert outcome.events[0].urgent and outcome.events[0].line.startswith("Sécurité, URGENT")


def test_a_finding_that_goes_and_comes_back_is_told_again() -> None:
    made = report(finding("hygiene.docker", "fix"))
    gone = run(state(security_told=("hygiene.docker",)), report())
    assert gone.told == ()

    assert lines(run(state(security_told=gone.told), made))


def test_the_first_pass_takes_note_and_tells_nothing() -> None:
    outcome = run(notify.State(known=True), report(finding("hygiene.docker", "fix"), finding("drift.pi.sensitive", "watch")))

    assert outcome.events == [] and outcome.known is True
    assert outcome.told == ("hygiene.docker",)
    assert "drift.pi.sensitive" in outcome.watch_since


def test_a_fresh_installation_says_nothing() -> None:
    assert run(notify.State(), report(finding("hygiene.docker", "fix"))).events == []


def test_nothing_is_told_when_there_is_no_report() -> None:
    previous = state(security_told=("a",), watch_since={"b": MORNING.isoformat()}, digest_day="2026-11-19")
    outcome = run(previous, None)

    assert outcome.events == [] and outcome.told == ("a",) and outcome.digest_day == "2026-11-19"


def test_what_is_to_watch_goes_in_one_message_a_day_with_its_age() -> None:
    made = report(finding("exposure.ssh", "watch", "SSH écoute partout"), finding("host.pi.updates", "watch", "Mises à jour en attente"))
    since = {"exposure.ssh": (MORNING - timedelta(days=3)).isoformat(), "host.pi.updates": (MORNING - timedelta(minutes=20)).isoformat()}

    outcome = run(state(watch_since=since, digest_day="2026-11-19"), made)

    assert lines(outcome) == [
        "Sécurité : 2 point(s) à surveiller.",
        "· SSH écoute partout (depuis 3 j)",
        "· Mises à jour en attente (depuis moins d'une heure)",
    ]
    assert not any(event.urgent for event in outcome.events)
    assert outcome.digest_day == "2026-11-20"

    assert run(state(watch_since=since, digest_day="2026-11-20"), made).events == []


def test_the_digest_waits_for_its_hour_and_a_watch_that_comes_later_waits_for_tomorrow() -> None:
    made = report(finding("exposure.ssh", "watch"))

    assert run(state(digest_day="2026-11-19"), made, now=EARLY).events == []

    afternoon = datetime(2026, 11, 20, 13, 0, tzinfo=timezone.utc)
    done = run(state(digest_day="2026-11-20"), made, now=afternoon)
    assert done.events == []


def test_no_digest_when_there_is_nothing_to_watch() -> None:
    outcome = run(state(digest_day="2026-11-19"), report(finding("logs.ssh", "information")))
    assert outcome.events == [] and outcome.digest_day == "2026-11-20"


def test_a_stale_report_is_said_in_the_digest() -> None:
    old = MORNING - timedelta(hours=7)
    outcome = run(state(digest_day="2026-11-19"), report(collected=old))

    assert lines(outcome) == ["Le rapport de sécurité n'a pas été refait depuis 7 h : la vigie ne surveille plus."]


def test_a_window_holds_the_drift_and_says_so_in_the_digest() -> None:
    opened = window.Window(MORNING - timedelta(hours=1), MORNING + timedelta(hours=1))
    made = report(
        finding("drift.pi.sensitive", "watch", "pi : changement sensible"),
        finding("exposure.ssh", "watch", "SSH écoute partout"),
    )

    outcome = run(state(digest_day="2026-11-19"), made, opened=opened)

    assert lines(outcome) == [
        "Sécurité : 1 point(s) à surveiller.",
        "· SSH écoute partout (depuis moins d'une heure)",
        "· Une fenêtre de maintenance est ouverte jusqu'à 10:30 : 1 point(s) de dérive sont comptés, pas signalés.",
    ]


def test_a_window_holds_drift_to_fix_but_never_the_rest_nor_urgent() -> None:
    opened = window.Window(MORNING - timedelta(hours=1), MORNING + timedelta(hours=1))
    made = report(
        finding("drift.pi.sensitive", "fix", "dérive"),
        finding("hygiene.docker", "fix", "socket"),
        finding("drift.pi.other", "urgent", "dérive grave"),
    )

    outcome = run(state(), made, opened=opened)

    assert [line for line in lines(outcome) if not line.startswith("·")] == [
        "Sécurité, à corriger — socket",
        "Sécurité, URGENT — dérive grave",
    ]
    assert "drift.pi.sensitive" not in outcome.told

    after = run(state(security_told=outcome.told), made)
    assert lines(after) == ["Sécurité, à corriger — dérive"]


def test_a_window_that_ran_out_is_told_once() -> None:
    gone = window.Window(MORNING - timedelta(hours=3), MORNING - timedelta(minutes=1))
    outcome = run(state(), report(), expired=gone)

    assert lines(outcome) == ["Sécurité : la fenêtre de maintenance est terminée, la dérive des fichiers est de nouveau signalée."]


def test_the_state_keeps_the_security_fields(tmp_path: Path) -> None:
    kept = notify.State(
        known=True, security_known=True, security_told=("a", "b"), watch_since={"c": "2026-11-20T08:30:00+00:00"}, digest_day="2026-11-20"
    )
    notify.write_state(tmp_path, kept)

    read = notify.read_state(tmp_path)
    assert (read.security_known, read.security_told, read.watch_since, read.digest_day) == (True, ("a", "b"), kept.watch_since, "2026-11-20")


def test_a_state_written_before_the_slice_reads_as_a_first_pass(tmp_path: Path) -> None:
    (tmp_path / notify.STATE).parent.mkdir(parents=True)
    (tmp_path / notify.STATE).write_text(json.dumps({"score": 90, "findings": []}), encoding="utf-8")

    assert notify.read_state(tmp_path).security_known is False


class Recorder(notify.Gotify):
    sent: list[notify.Message] = []

    def send(self, message, click="", post=None):  # type: ignore[no-untyped-def,override]
        self.sent.append(message)


def _write_report(generated: Path, *findings: dict) -> None:
    (generated / series.REPORT).write_text(
        json.dumps({"security": {**report(*findings, collected=datetime.now(timezone.utc))}}), encoding="utf-8"
    )


def test_the_vigil_tells_a_new_finding_to_fix_and_records_the_series(tmp_path: Path) -> None:
    recorder = Recorder("https://g", "t")
    recorder.sent = []

    _write_report(tmp_path)
    assert vigil.one_pass(tmp_path, recorder, dry_run=False, render=False) == 0
    assert recorder.sent == []

    _write_report(tmp_path, finding("hygiene.docker", "fix", "Un conteneur a le socket Docker"))
    assert vigil.one_pass(tmp_path, recorder, dry_run=False, render=False) == 0

    assert [message.body for message in recorder.sent] == ["Sécurité, à corriger — Un conteneur a le socket Docker"]
    assert len(series.read(tmp_path)) == 2


def test_a_gotify_that_does_not_answer_leaves_no_gap_in_the_series_and_tells_again(tmp_path: Path) -> None:
    class Down(notify.Gotify):
        def send(self, message, click="", post=None):  # type: ignore[no-untyped-def,override]
            raise OSError("refused")

    _write_report(tmp_path)
    vigil.one_pass(tmp_path, None, dry_run=False, render=False)
    _write_report(tmp_path, finding("hygiene.docker", "fix", "socket"))

    assert vigil.one_pass(tmp_path, Down("https://g", "t"), dry_run=False, render=False) == 1
    assert len(series.read(tmp_path)) == 2

    recorder = Recorder("https://g", "t")
    recorder.sent = []
    assert vigil.one_pass(tmp_path, recorder, dry_run=False, render=False) == 0
    assert "socket" in recorder.sent[0].body


def test_a_dry_run_keeps_nothing_of_security(tmp_path: Path) -> None:
    _write_report(tmp_path, finding("hygiene.docker", "fix"))
    vigil.one_pass(tmp_path, None, dry_run=True, render=False)

    assert not (tmp_path / series.SERIES).exists()


def test_a_window_that_ran_out_is_closed_by_the_pass(tmp_path: Path) -> None:
    now = datetime.now(timezone.utc)
    window.open_window(tmp_path, now - timedelta(hours=3), timedelta(hours=1), 4)
    _write_report(tmp_path)

    vigil.one_pass(tmp_path, None, dry_run=False, render=False)
    vigil.one_pass(tmp_path, None, dry_run=False, render=False)

    assert window.read(tmp_path) is None
    assert '"expired"' in (tmp_path / window.JOURNAL).read_text(encoding="utf-8")


class _Done:
    def __init__(self, code: int, out: str = "", err: str = "") -> None:
        self.returncode, self.stdout, self.stderr = code, out, err


def test_the_vigil_runs_the_assessment_then_the_renders(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    ran: list[object] = []

    monkeypatch.setattr(vigil, "_assess", lambda generated: ran.append(("assess", generated)))
    monkeypatch.setattr(vigil, "_boot_check", lambda generated: ran.append(("boot", generated)))
    monkeypatch.setattr(vigil, "_run", lambda module: ran.append(module))
    monkeypatch.setattr(vigil, "first_renders", lambda generated, run=None: [])
    vigil._render(tmp_path)

    assert ran == [("assess", tmp_path), ("boot", tmp_path), *vigil.RENDERS]


def test_the_start_up_checks_are_run_with_the_data_directory_and_every_verdict_is_an_answer(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    seen: list[list[str]] = []
    monkeypatch.setattr(vigil.subprocess, "run", lambda command, **kwargs: seen.append(command) or _Done(2, "Start: 1 to fix"))

    vigil._boot_check(tmp_path)

    assert seen[0][1:] == ["-m", "aistack.cli.boot_check", "--once", "--ai", "--output", str(tmp_path)]
    assert capsys.readouterr().out == ""

    def too_slow(*args: object, **kwargs: object) -> None:
        raise vigil.subprocess.TimeoutExpired("boot_check", vigil.BOOT_CHECK_SECONDS)

    monkeypatch.setattr(vigil.subprocess, "run", too_slow)
    vigil._boot_check(tmp_path)

    assert f"no answer within {vigil.BOOT_CHECK_SECONDS} s; the verdict of the previous pass stands" in capsys.readouterr().out

    monkeypatch.setattr(vigil.subprocess, "run", lambda *a, **k: _Done(1 if False else 126, "", "No module named aistack.cli.boot_check"))
    vigil._boot_check(tmp_path)

    assert "exit 126: No module named aistack.cli.boot_check" in capsys.readouterr().out


def test_the_assessment_is_run_with_the_data_directory(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    seen: list[list[str]] = []
    monkeypatch.setattr(vigil.subprocess, "run", lambda command, **kwargs: seen.append(command) or _Done(0))

    vigil._assess(tmp_path)

    assert seen[0][1:] == ["-m", "aistack.cli.security_assess", str(tmp_path)]


def test_exit_one_with_a_report_is_an_answer_not_a_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(vigil.subprocess, "run", lambda *a, **k: _Done(1, "Security assessment: 0 urgent, 1 fix, 0 watch, 2 information — x\n"))

    vigil._assess(tmp_path)

    assert capsys.readouterr().out == ""


def test_exit_one_without_a_report_is_said(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(
        vigil.subprocess, "run", lambda *a, **k: _Done(1, "", "No module named aistack.cli.security_assess")
    )

    vigil._assess(tmp_path)

    assert "exit 1: No module named aistack.cli.security_assess" in capsys.readouterr().out


def test_a_security_yml_that_cannot_be_read_does_not_stop_the_vigil(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    broken = tmp_path / "security.yml"
    broken.write_text("digest_hour: 99\n", encoding="utf-8")
    monkeypatch.setattr(vigil, "SECURITY", broken)

    assert vigil._security_definition() == SecurityDefinition()
    assert "security.yml not read" in capsys.readouterr().out
