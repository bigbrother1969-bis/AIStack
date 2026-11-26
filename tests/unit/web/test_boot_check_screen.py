"""`/boot-check/` and `/boot-state` (ADR-0032, slice B3), and the strip's label in the console."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from aistack.boot_checks.controls import Result
from aistack.boot_checks.state import Explanation, Incident, Verdict, read_verdict, write_verdict
from aistack.web.app import WebPaths, create_app
from tests.unit.web.test_api_keys_settings import LANGUAGES, LISTENERS
from tests.unit.web_signed_in import signed_in


def client(tmp_path: Path, port: int = 8186) -> TestClient:
    app = create_app(tmp_path, LISTENERS, LANGUAGES, WebPaths())
    return TestClient(app, base_url=f"http://testserver:{port}", follow_redirects=False)


def write(tmp_path: Path, overall: str = "ok") -> None:
    now = datetime.now(timezone.utc)
    started = now.replace(microsecond=0).isoformat()
    results = (
        Result("mounts", "ok", "2 of 2 mounts present", ()),
        Result("containers", "warning", "1 expected container missing", ("olala",)),
        Result("ups", "skipped", "nothing declared", ()),
    )
    incident = Incident("containers", "warning", started, "1 expected container missing", None)
    write_verdict(tmp_path, Verdict(overall, 1 if overall != "ok" else 0, now.isoformat(), "b", started, results, (incident,)))


def test_the_state_is_empty_without_a_session_and_says_how_the_start_goes_with_one(tmp_path: Path) -> None:
    write(tmp_path)

    assert client(tmp_path).get("/boot-state").json() == {}

    found = signed_in(client(tmp_path)).get("/boot-state?lang=fr").json()["pills"][0]

    assert found["level"] == "clean" and found["status"] == "ok"
    assert found["text"].startswith("Démarrage : tout va bien depuis")


def test_without_a_verdict_the_state_is_not_judged_never_green(tmp_path: Path) -> None:
    found = signed_in(client(tmp_path)).get("/boot-state?lang=en").json()["pills"][0]

    assert (found["level"], found["status"], found["text"]) == ("not-instrumented", "unknown", "Start: not judged")


def test_an_anomaly_is_counted_in_the_strip(tmp_path: Path) -> None:
    write(tmp_path, "warning")

    assert signed_in(client(tmp_path)).get("/boot-state?lang=en").json()["pills"][0]["text"].startswith("Start: 1 to watch")


def test_the_page_lists_the_controls_the_names_and_the_incidents(tmp_path: Path) -> None:
    write(tmp_path, "warning")
    page = signed_in(client(tmp_path)).get("/boot-check/?lang=en").text

    assert "Start-up checks" in page and "2 of 2 mounts present" in page
    assert "<code>olala</code>" in page and "still failing" in page
    assert "not checked" in page and "--suggest" in page


def test_the_page_without_a_verdict_says_so_and_is_lan_only(tmp_path: Path) -> None:
    assert "No verdict yet" in signed_in(client(tmp_path)).get("/boot-check/?lang=en").text
    assert client(tmp_path, port=8183).get("/boot-check/").status_code in (403, 404)


def test_the_script_is_added_for_a_signed_in_page_only(tmp_path: Path) -> None:
    (tmp_path / "console.html").write_text('<html><body><a id="boot-indicator">x</a></body></html>', encoding="utf-8")

    assert "/boot-state" not in client(tmp_path).get("/console.html").text
    assert "/boot-state" in signed_in(client(tmp_path)).get("/console.html").text


def test_the_cartouche_has_the_static_label_that_links_to_the_page() -> None:
    from aistack.health.cockpit import HealthCockpit, HealthDomain
    from aistack.renderers.console.html import render_html
    from tests.unit.renderers.console.test_console_html import selection_ui_link

    document = render_html((selection_ui_link(),), cockpit=HealthCockpit(domains=(HealthDomain(name="Stockage", instrumented=True),)))

    assert 'id="boot-indicator"' in document and 'href="/boot-check/"' in document
    assert "Contrôles du démarrage" in document and "<script" not in document


def test_a_companion_has_its_own_pill_and_its_own_part_of_the_page(tmp_path: Path) -> None:
    write(tmp_path)
    now = datetime.now(timezone.utc)
    started = (now.replace(microsecond=0)).isoformat()
    write_verdict(
        tmp_path,
        Verdict("critical", 1, now.isoformat(), "b2", started, (Result("reachable", "critical", "boot-facts.json is old", ()),), ()),
        "backup-host",
    )
    web = signed_in(client(tmp_path))
    pills = web.get("/boot-state?lang=en").json()["pills"]

    assert [pill["host"] for pill in pills] == ["", "backup-host"]
    assert pills[1]["text"].startswith("Start of backup-host: 1 to fix") and pills[1]["level"] == "alert"

    page = web.get("/boot-check/?lang=en").text

    assert 'id="backup-host"' in page and "Machine backup-host" in page and "boot-facts.json is old" in page
    assert "Reachable" in page


def test_the_page_says_the_circumstances_and_marks_the_extra_controls(tmp_path: Path) -> None:
    now = datetime.now(timezone.utc)
    started = now.replace(microsecond=0).isoformat()
    results = (Result("mounts", "ok", "2 of 2 mounts present"), Result("kernel_disk_errors", "ok", "no disk or file-system error in the kernel log since the start"))
    write_verdict(
        tmp_path,
        Verdict("ok", 0, now.isoformat(), "b", started, results, (), "", ("unclean_previous_stop",), ("kernel_disk_errors",)),
    )
    page = signed_in(client(tmp_path)).get("/boot-check/?lang=en").text

    assert "Circumstances:" in page and "the previous stop was not clean" in page
    assert page.count("(extra)") == 1 and "Kernel disk errors" in page


def test_without_a_circumstance_the_page_says_the_base_controls_are_enough(tmp_path: Path) -> None:
    write(tmp_path)

    assert "none, the base controls are enough." in signed_in(client(tmp_path)).get("/boot-check/?lang=en").text


def test_the_page_shows_the_engine_s_words_under_the_anomaly_they_concern_and_only_then(tmp_path: Path) -> None:
    write(tmp_path, "warning")
    verdict = read_verdict(tmp_path)
    assert verdict is not None
    said = Explanation("containers", "warning", "1 expected container missing", "Un conteneur attendu ne tourne pas.", "olala", "2026-11-26T09:00:00+00:00")
    stale = Explanation("containers", "warning", "2 expected containers missing", "Texte périmé.", "olala", "2026-11-26T09:00:00+00:00")

    write_verdict(tmp_path, replace(verdict, explanations=(stale, said)))
    page = signed_in(client(tmp_path)).get("/boot-check/?lang=fr").text

    assert "Un conteneur attendu ne tourne pas." in page and "non vérifiée" in page and "Texte périmé" not in page

    write_verdict(tmp_path, replace(verdict, explanations=(replace(said, text=""),)))

    assert "non vérifiée" not in signed_in(client(tmp_path)).get("/boot-check/?lang=fr").text
