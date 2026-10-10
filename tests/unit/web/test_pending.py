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


def test_nothing_without_a_session_nor_on_the_public_port(tmp_path: Path):
    assert client(tmp_path).get("/pending").json() == {}
    assert signed_in(client(tmp_path, port=8183)).get("/pending").status_code == 404


def test_the_counts_read_the_proposals_waiting_and_the_vigil_s_findings(tmp_path: Path):
    from aistack.dock import proposals
    from aistack.vigil import snapshot

    change = proposals.ImageChange(container="wordpress", image="wordpress:7", from_digest="a", to_digest="b")
    proposals.propose(tmp_path, "wordpress", [change], "security fix for the site", "fabrice")
    snapshot.write(snapshot.Snapshot(at="2026-10-10T08:00:00+00:00", score=88, debt=55, findings=(
        snapshot.SnapshotFinding(key="k", domain="Tests PRA", subject="gigabyte", text="t"),
    )), tmp_path)

    assert pending.counts(tmp_path) == {"/dock/": 1, "/troubleshooting/": 1}


def test_the_lan_cards_carry_their_path_and_the_notice_script_draws_the_pastille():
    from aistack.contracts.console_link import ConsoleLink
    from aistack.renderers.console.html import render_html
    from aistack.web.notifications import snippet
    from aistack.i18n import translator_for

    page = render_html((ConsoleLink(name="Dock", description="d", url="http://GIGABYTE:8186/dock/", scope="lan"),))

    assert 'data-pending="/dock/"' in page and "<script" not in page
    assert 'fetch("/pending"' in snippet(translator_for("fr"))
