"""The console cards' pastilles (2026-10-10): `/pending`, the cards' `data-pending`, the script that draws them."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from tests.unit.web.test_api_keys_settings import LANGUAGES, LISTENERS
from tests.unit.web_signed_in import signed_in

from aistack.web import pending
from aistack.web.app import WebPaths, create_app


def client(tmp_path: Path, port: int = 8186, counts=None) -> TestClient:
    app = create_app(
        tmp_path, LISTENERS, LANGUAGES, WebPaths(),
        pending_counts=counts or (lambda generated: {"/dock/": 1, "/troubleshooting/": 3}),
    )
    return TestClient(app, base_url=f"http://testserver:{port}", follow_redirects=False)


def test_a_signed_in_person_on_the_lan_gets_each_card_s_count_and_text(tmp_path: Path):
    reply = signed_in(client(tmp_path)).get("/pending?lang=fr")

    assert reply.json() == {
        "/dock/": {"count": 1, "text": "1 mise(s) à jour à valider"},
        "/troubleshooting/": {"count": 3, "text": "3 constat(s) à traiter"},
    }


def test_nothing_without_a_session_and_the_counts_on_both_listeners_with_one(tmp_path: Path):
    assert client(tmp_path).get("/pending").json() == {}
    assert client(tmp_path, port=8183).get("/pending").json() == {}
    assert signed_in(client(tmp_path, port=8183)).get("/pending").json()["/dock/"]["count"] == 1


def test_the_counts_read_the_proposals_waiting_and_the_vigil_s_findings(tmp_path: Path):
    from aistack.dock import proposals
    from aistack.vigil import snapshot

    change = proposals.ImageChange(container="wordpress", image="wordpress:7", from_digest="a", to_digest="b")
    proposals.propose(tmp_path, "wordpress", [change], "security fix for the site", "fabrice")
    snapshot.write(snapshot.Snapshot(at="2026-10-10T08:00:00+00:00", score=88, debt=55, findings=(
        snapshot.SnapshotFinding(key="k", domain="Tests PRA", subject="gigabyte", text="t"),
    )), tmp_path)

    assert pending.counts(tmp_path) == {"/dock/": 1, "/troubleshooting/": 1}


def test_the_lan_cards_carry_their_path_and_the_page_script_draws_the_pastille(tmp_path: Path):
    from aistack.contracts.console_link import ConsoleLink
    from aistack.renderers.console.html import render_html

    page = render_html((ConsoleLink(name="Dock", description="d", url="http://GIGABYTE:8186/dock/", scope="lan"),))
    assert 'data-pending="/dock/"' in page and "<script" not in page

    (tmp_path / "console.html").write_text(page, encoding="utf-8")
    for port in (8183, 8186):
        served = signed_in(client(tmp_path, port=port)).get("/console.html").text
        assert 'fetch("/pending"' in served, port
    assert 'fetch("/pending"' not in client(tmp_path, port=8183).get("/console.html").text


def write_security(directory: Path, *findings: tuple[str, str]) -> None:
    import json
    from datetime import datetime, timezone

    report = {"security": {"collected_at": datetime.now(timezone.utc).isoformat(), "measures": {}, "findings": [
        {"key": key, "severity": severity, "title": key, "evidence": [], "unknown": ""} for key, severity in findings
    ]}}
    (directory / "security-assessment.json").write_text(json.dumps(report), encoding="utf-8")


def test_the_security_card_counts_watch_and_worse_and_takes_the_colour_of_the_worst(tmp_path: Path):
    write_security(tmp_path, ("exposure.x", "watch"), ("hygiene.docker_socket", "fix"), ("images.old", "information"))

    assert pending.counts(tmp_path) == {"/security/": 2}
    item = signed_in(client(tmp_path, counts=pending.counts)).get("/pending?lang=fr").json()["/security/"]
    assert item == {
        "count": 2,
        "text": "2 constat(s) de sécurité ouverts, le pire : à corriger",
        "level": "fix",
        "label": "à corriger",
    }


def test_nothing_is_drawn_on_the_security_card_when_nothing_counts(tmp_path: Path):
    write_security(tmp_path, ("images.old", "information"))

    assert "/security/" not in pending.counts(tmp_path)
    assert "/security/" not in signed_in(client(tmp_path, counts=pending.counts)).get("/pending").json()


def test_the_findings_a_maintenance_window_holds_are_not_counted(tmp_path: Path):
    from datetime import datetime, timedelta, timezone

    from aistack.security import window

    write_security(tmp_path, ("drift.msi.sensitive", "watch"), ("drift.msi.other", "fix"))
    assert pending.counts(tmp_path) == {"/security/": 2}

    window.open_window(tmp_path, datetime.now(timezone.utc), timedelta(hours=1), 4)
    assert "/security/" not in pending.counts(tmp_path)


def test_the_security_pastille_has_its_own_colours_shape_and_word_so_it_is_not_taken_for_a_queue(tmp_path: Path):
    snippet = pending.SNIPPET

    for level in ("watch", "fix", "urgent"):
        assert f".pending-level-{level}" in snippet
    assert "item.label" in snippet and "pending-level" in snippet
    # The queues' pastille keeps its own style.
    assert "#c2410c" in snippet and "border-radius: .7rem" in snippet


def test_the_security_card_is_known_to_the_console_and_carries_its_path(tmp_path: Path):
    from aistack.contracts.console_link import ConsoleLink
    from aistack.renderers.console.html import render_html

    page = render_html((ConsoleLink(name="Sécurité", description="d", url="http://GIGABYTE:8186/security/", scope="lan"),))

    assert 'data-pending="/security/"' in page
