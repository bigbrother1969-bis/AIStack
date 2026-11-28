"""
`aistack.web.simple_console` (ADR-0033). CN0 : le routeur répond sur
les deux formes, sur les deux écouteurs, exige une session (comme
Architecture et le Health cockpit, ADR-0014 § 5). CN1 : la maquette
(variante C). CN2 : les quatre jauges lisent de vrais signaux déjà
calculés ailleurs — rien n'est inventé ici, chaque test écrit la trace
réelle que le signal attend et vérifie que la jauge la restitue.
"""

from __future__ import annotations

import json
import socket
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from tests.conftest import use_source
from tests.unit.web_signed_in import signed_in

from aistack.dock.proposals import FAILED, Proposal, proposals_dir, save
from aistack.i18n import Language, Languages
from aistack.web.app import create_app
from aistack.web.exposure import Listeners

PUBLIC_PORT = 8183
LAN_PORT = 8186
LISTENERS = Listeners(public_port=PUBLIC_PORT, lan_port=LAN_PORT)
LANGUAGES = Languages(
    reference="fr",
    available=(Language("fr", "Français"), Language("en", "English")),
)


def client(generated: Path, port: int = LAN_PORT) -> TestClient:
    return TestClient(
        create_app(generated, LISTENERS, LANGUAGES),
        base_url=f"http://testserver:{port}",
        follow_redirects=False,
    )


@pytest.mark.parametrize("port", [PUBLIC_PORT, LAN_PORT])
@pytest.mark.parametrize("path", ["/simple", "/simple/"])
def test_signed_out_it_leads_to_sign_in(generated: Path, port: int, path: str):
    """ADR-0014 § 5: no session, no infrastructure status."""

    reply = client(generated, port).get(path)

    assert reply.status_code == 303
    assert reply.headers["location"] == f"/login?next={quote(path, safe='')}"


@pytest.mark.parametrize("port", [PUBLIC_PORT, LAN_PORT])
@pytest.mark.parametrize("path", ["/simple", "/simple/"])
def test_signed_in_the_screen_answers_on_both_listeners(generated: Path, port: int, path: str):
    reply = signed_in(client(generated, port)).get(path)

    assert reply.status_code == 200
    assert "text/html" in reply.headers["content-type"]


def test_the_four_gauges_and_the_advanced_link_are_there(generated: Path):
    body = signed_in(client(generated)).get("/simple").text

    for label in ("Sécurité", "Sauvegardes", "Espace disque", "Mises à jour"):
        assert label in body
    assert 'href="/console.html"' in body
    assert "Mode avancé (console complète)" in body


def test_with_nothing_measured_the_screen_stays_neutral(generated: Path):
    """No security report, no boot-check verdict, no declared storage
    threshold for this host, no dock proposal: Sécurité and Mises à
    jour read as settled (nothing to report), Sauvegardes and Espace
    disque as not measured — none of the four is an issue to act on."""

    body = signed_in(client(generated)).get("/simple").text

    assert "Protégée" in body  # Sécurité : aucun constat
    assert "À jour" in body  # Mises à jour : aucune proposition
    assert body.count("Non mesuré") == 2  # Sauvegardes et Espace disque
    assert "Demander à l'IA de régler ça" not in body
    assert "Tout est vert" in body


def test_a_security_finding_shows_the_ai_button(generated: Path):
    (generated / "security-assessment.json").write_text(
        json.dumps({"security": {"findings": [{"key": "exposure.port", "severity": "fix", "title": "x"}]}}),
        encoding="utf-8",
    )

    body = signed_in(client(generated)).get("/simple").text

    assert "constat(s) à traiter" in body
    assert body.count("Demander à l'IA de régler ça") == 1
    assert "Un point mérite votre attention" in body


def test_a_boot_check_anomaly_shows_the_ai_button(generated: Path):
    now = datetime.now(timezone.utc).isoformat()
    (generated / "boot-check.json").write_text(
        json.dumps({"overall": "critical", "anomalies": 2, "checked_at": now, "booted_at": now}),
        encoding="utf-8",
    )

    body = signed_in(client(generated)).get("/simple").text

    assert "anomalie(s) à corriger" in body
    assert body.count("Demander à l'IA de régler ça") == 1


def test_a_storage_shortage_shows_the_ai_button(generated: Path, monkeypatch: pytest.MonkeyPatch):
    host = socket.gethostname()
    mount = generated / "volume"
    mount.mkdir()
    thresholds = generated / "storage_thresholds.yml"
    thresholds.write_text(
        f"""
hosts:
  - host: {host}
    thresholds:
      - mount: {mount}
        kind: free_bytes
        free_gb: 999999999
""",
        encoding="utf-8",
    )
    use_source(monkeypatch, "storage_thresholds", thresholds)

    body = signed_in(client(generated)).get("/simple").text

    assert "volume(s) à surveiller" in body
    assert body.count("Demander à l'IA de régler ça") == 1


def test_a_failed_update_proposal_shows_the_ai_button(generated: Path):
    proposals_dir(generated).mkdir(parents=True, exist_ok=True)
    save(
        generated,
        Proposal(
            id="0001",
            service="aistack-core",
            changes=[],
            why="test",
            proposed_by="tester",
            proposed_at=datetime.now(timezone.utc).isoformat(),
            status=FAILED,
        ),
    )

    body = signed_in(client(generated)).get("/simple").text

    assert "Une mise à jour a échoué" in body
    assert body.count("Demander à l'IA de régler ça") == 1


def test_a_pending_update_proposal_shows_the_ai_button(generated: Path):
    save(
        generated,
        Proposal(
            id="0001",
            service="aistack-core",
            changes=[],
            why="test",
            proposed_by="tester",
            proposed_at=datetime.now(timezone.utc).isoformat(),
        ),  # status defaults to PROPOSED
    )

    body = signed_in(client(generated)).get("/simple").text

    assert "Une mise à jour attend une décision" in body
    assert body.count("Demander à l'IA de régler ça") == 1
