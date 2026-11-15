"""What appeared is said by the vigil once, with the other events (ADR-0026)."""

from __future__ import annotations

from pathlib import Path

import pytest

from aistack.arrivals import state
from aistack.arrivals.detect import CONTAINER, HOST, Arrival
from aistack.cli import vigil
from aistack.i18n import translator_for
from aistack.vigil import notify, snapshot

T = translator_for("fr")
KEY = "findings.inventory_gap.undeclared_here.interpretation"


@pytest.fixture(autouse=True)
def no_docker(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*args: object, **kwargs: object) -> None:
        raise OSError("no docker here")

    monkeypatch.setattr("aistack.arrivals.facts.subprocess.run", refuse)


def undeclared(*names: str) -> snapshot.Snapshot:
    findings = tuple(
        snapshot.SnapshotFinding(
            snapshot.finding_key("Écarts d'inventaire", name, KEY), "Écarts d'inventaire", name, f"{name} runs", ((KEY, (("container", name),)),)
        )
        for name in names
    )

    return snapshot.Snapshot("2026-11-15T12:00:00+00:00", 90, 80, findings)


class Recorder(notify.Gotify):
    sent: list[notify.Message] = []

    def send(self, message, click="", post=None):  # type: ignore[no-untyped-def,override]
        self.sent.append(message)


class Down(notify.Gotify):
    def send(self, message, click="", post=None):  # type: ignore[no-untyped-def,override]
        raise OSError("connection refused")


def test_the_lines():
    assert notify.arrival_event(T, Arrival(CONTAINER, "koboldcpp")).line == (
        "Nouveau conteneur non déclaré : koboldcpp — à déclarer dans « Nouveautés »."
    )
    assert "sur 192.168.1.11" in notify.arrival_event(T, Arrival(CONTAINER, "grafana", "192.168.1.11")).line
    assert notify.arrival_event(T, Arrival(HOST, "192.168.1.60", "pi")).line == (
        "Nouvelle machine avec Docker : 192.168.1.60 (utilisateur pi) — voir « Nouveautés »."
    )
    assert not notify.arrival_event(T, Arrival(HOST, "192.168.1.60", "pi")).urgent


def test_a_new_container_is_said_once_on_its_second_pass(tmp_path: Path):
    recorder = Recorder("https://g", "t")
    recorder.sent = []

    for found in (undeclared("ollama"), undeclared("ollama", "koboldcpp"), undeclared("ollama", "koboldcpp"), undeclared("ollama", "koboldcpp")):
        snapshot.write(found, tmp_path)
        assert vigil.one_pass(tmp_path, recorder, dry_run=False, render=False) == 0

    assert [m.body for m in recorder.sent] == ["Nouveau conteneur non déclaré : koboldcpp — à déclarer dans « Nouveautés »."]
    assert recorder.sent[0].title == "AIStack — 1 nouveauté(s)"


def test_a_message_gotify_refused_is_tried_again_at_the_next_pass(tmp_path: Path):
    for found in (undeclared("ollama"), undeclared("ollama", "koboldcpp")):
        snapshot.write(found, tmp_path)
        vigil.one_pass(tmp_path, None, dry_run=False, render=False)

    snapshot.write(undeclared("ollama", "koboldcpp"), tmp_path)
    assert vigil.one_pass(tmp_path, Down("https://g", "t"), dry_run=False, render=False) == 1
    assert state.read_state(tmp_path)["containers"]["koboldcpp"]["announced"] is False

    recorder = Recorder("https://g", "t")
    recorder.sent = []
    assert vigil.one_pass(tmp_path, recorder, dry_run=False, render=False) == 0
    assert "koboldcpp" in recorder.sent[0].body


def test_a_dry_run_keeps_nothing(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    snapshot.write(undeclared("ollama"), tmp_path)
    vigil.one_pass(tmp_path, None, dry_run=True, render=False)

    assert state.read_state(tmp_path) == {}


def test_a_broken_declaration_does_not_stop_the_vigil(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]):
    broken = tmp_path / "arrivals.yml"
    broken.write_text("confirm_passes: 0\n", encoding="utf-8")
    monkeypatch.setattr(vigil, "ARRIVALS", broken)
    snapshot.write(undeclared("ollama"), tmp_path)

    assert vigil.one_pass(tmp_path, None, dry_run=False, render=False) == 0
    assert "arrivals skipped" in capsys.readouterr().out
