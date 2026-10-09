"""The vigil and its Gotify notifications (2.0, 2026-10-09)."""

from __future__ import annotations

import json
from pathlib import Path

from aistack.cli import vigil
from aistack.dock import proposals as store
from aistack.health.cockpit import HealthCockpit, HealthDomain
from aistack.hosts.health import evaluate_silent_hosts
from aistack.contracts.host_silence import HostSilence
from aistack.i18n import translator_for
from aistack.vigil import notify, snapshot

T = translator_for("fr")


def _proposal(id_: str, status: str) -> store.Proposal:
    return store.Proposal(id_, "wordpress", [], "nouvelle version de sécurité", "fabrice", "2026-10-09T08:00:00+00:00", status)


def _snapshot(score: int, *findings: snapshot.SnapshotFinding) -> snapshot.Snapshot:
    return snapshot.Snapshot("2026-10-09T08:00:00+00:00", score, 70, findings)


def _finding(domain: str, subject: str, kind: str, message: tuple = ()) -> snapshot.SnapshotFinding:
    return snapshot.SnapshotFinding(snapshot.finding_key(domain, subject, kind), domain, subject, f"{subject} text", message)


def test_the_first_pass_only_takes_note() -> None:
    found, state = notify.events(T, notify.State(), _snapshot(81, _finding("Tests PRA", "vikunja", "x")), [_proposal("p1", store.PROPOSED)])
    assert found == []
    assert state.score == 81 and state.findings and state.proposals == {"p1": store.PROPOSED}


def test_a_new_silent_host_rings_and_is_said_once() -> None:
    previous = notify.State(known=True, score=81, findings=(), proposals={})
    (finding,) = evaluate_silent_hosts([HostSilence("raspberry", "/media/BACKUP/x", problem="not mounted")])
    cockpit = HealthCockpit(domains=(HealthDomain("Hôtes", True, (finding,)),))
    now = snapshot.take(cockpit, 81, 70)

    found, state = notify.events(T, previous, now, [])
    (event,) = found
    assert event.urgent and event.line.startswith("Hôte silencieux — Aucun relevé du collecteur de l'hôte raspberry")

    again, _ = notify.events(T, state, now, [])
    assert again == []


def test_a_failed_restore_test_rings() -> None:
    previous = notify.State(known=True, score=81, findings=(), proposals={})
    failed = _finding(
        "Tests PRA", "immich", notify.PRA_FAILED,
        message=((notify.PRA_FAILED, (("service", "immich"),)),),
    )
    found, _ = notify.events(T, previous, _snapshot(81, failed), [])
    (event,) = found
    assert event.urgent and "immich" in event.line and event.line.startswith("Test de restauration échoué")


def test_the_health_going_down_lists_its_new_findings() -> None:
    old = _finding("Services", "nginx", "a")
    previous = notify.State(known=True, score=81, findings=(old.key,), proposals={})
    new = _finding("Stockage", "/media", "b")
    found, state = notify.events(T, previous, _snapshot(76, old, new), [])
    assert [e.line for e in found] == ["Santé en baisse : 81 → 76/100.", "· /media text"]
    assert not any(e.urgent for e in found)
    message = notify.compose(T, found)
    assert message is not None and message.title == "AIStack — 1 nouveauté(s)" and message.priority == notify.NORMAL

    # Going back up says nothing.
    up, _ = notify.events(T, state, _snapshot(90, old), [])
    assert up == []


def test_the_dock_proposed_then_rolled_back() -> None:
    previous = notify.State(known=True, score=81, findings=(), proposals={})
    found, state = notify.events(T, previous, None, [_proposal("p1", store.PROPOSED)])
    assert [e.line for e in found] == ["Quai : mise à jour de wordpress proposée par fabrice, en attente de validation."]

    found, state = notify.events(T, state, None, [_proposal("p1", store.VALIDATED)])
    assert found == []
    found, state = notify.events(T, state, None, [_proposal("p1", store.ROLLED_BACK)])
    (event,) = found
    assert event.urgent and "revenue en arrière" in event.line


def test_gotify_gets_one_grouped_message_with_its_token() -> None:
    sent: list[tuple[str, dict, dict]] = []
    gotify = notify.Gotify.from_environment({notify.URL_VARIABLE: "https://gotify.example/", notify.TOKEN_VARIABLE: "s3cret"})
    assert gotify is not None
    message = notify.compose(T, [notify.Event("dock", "a"), notify.Event("host", "b", urgent=True)])
    assert message is not None
    gotify.send(message, click="http://gigabyte:8186/console.html", post=lambda url, data, headers: sent.append((url, json.loads(data), headers)))

    ((url, payload, headers),) = sent
    assert url == "https://gotify.example/message" and headers["X-Gotify-Key"] == "s3cret"
    assert payload["message"] == "a\nb" and payload["priority"] == notify.URGENT
    assert payload["extras"]["client::notification"]["click"]["url"].endswith("/console.html")


def test_no_gotify_without_both_variables() -> None:
    assert notify.Gotify.from_environment({notify.URL_VARIABLE: "https://g"}) is None


def test_a_pass_keeps_its_state_and_retries_when_gotify_fails(tmp_path: Path, capsys) -> None:
    snapshot.write(_snapshot(81), tmp_path)
    assert vigil.one_pass(tmp_path, None, dry_run=False, render=False) == 0
    assert "first pass" in capsys.readouterr().out

    snapshot.write(_snapshot(70, _finding("Services", "nginx", "a")), tmp_path)

    class Down(notify.Gotify):
        def send(self, message, click="", post=None):  # type: ignore[override]
            raise OSError("connection refused")

    assert vigil.one_pass(tmp_path, Down("https://g", "t"), dry_run=False, render=False) == 1
    assert notify.read_state(tmp_path).score == 81  # not noted: tried again
    assert vigil.one_pass(tmp_path, None, dry_run=False, render=False) == 0
    out = capsys.readouterr().out
    assert "Santé en baisse : 81 → 70/100." in out and "notifications off" in out
    assert notify.read_state(tmp_path).score == 70


def test_the_snapshot_round_trips(tmp_path: Path) -> None:
    taken = _snapshot(81, _finding("Tests PRA", "immich", "k", message=(("k", (("service", "immich"),)),)))
    snapshot.write(taken, tmp_path)
    assert snapshot.read(tmp_path) == taken
