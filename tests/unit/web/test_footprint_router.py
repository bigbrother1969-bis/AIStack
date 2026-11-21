"""*Usage et empreinte* inside AIStack's web application (ADR-0030): a reading screen, LAN only, over the journal of AI calls."""

from __future__ import annotations

from datetime import datetime, timezone
from html import unescape
from pathlib import Path

from fastapi.testclient import TestClient

from tests.unit.web_signed_in import signed_in

from aistack.ai_runtime import call_journal
from aistack.ai_runtime.call_journal import Call
from aistack.i18n import Language, Languages
from aistack.web import footprint as footprint_screen
from aistack.web.app import WebPaths, create_app
from aistack.web.exposure import Listeners

PUBLIC_PORT = 8183
LAN_PORT = 8186
LISTENERS = Listeners(public_port=PUBLIC_PORT, lan_port=LAN_PORT)
LANGUAGES = Languages(reference="fr", available=(Language("fr", "Français"), Language("en", "English")))


def client(tmp_path: Path, port: int = LAN_PORT) -> TestClient:
    app = create_app(tmp_path, LISTENERS, LANGUAGES, WebPaths())

    return signed_in(TestClient(app, base_url=f"http://testserver:{port}", follow_redirects=False))


def record(tmp_path: Path, **more) -> None:
    base = dict(
        at=datetime.now(timezone.utc).isoformat(timespec="seconds"), caller="portal.chat", operation="ask",
        language="fr", answered_by="qwen2.5:7b", reached_external=False, reachable=True, seconds=12.5,
        policy_class="external_allowed", route="external_allowed; kind=question; chose qwen2.5:7b: stays inside",
        kind="question", gpu_watts=96.0,
    )
    call_journal.append(tmp_path / "ai-calls", Call(**{**base, **more}))


def test_before_any_call_the_page_counts_only_the_permanent_load(tmp_path: Path):
    reply = client(tmp_path).get("/footprint/?lang=en")
    text = unescape(reply.text)

    assert reply.status_code == 200
    assert "No AI call over the period" in text
    assert "AIStack's permanent load" in text
    assert 'href="/console.html?lang=en"' in text


def test_the_page_answers_with_and_without_the_trailing_slash(tmp_path: Path):
    assert client(tmp_path).get("/footprint?lang=en").status_code == 200


def test_the_page_shows_the_usage_the_levels_and_what_is_measured(tmp_path: Path):
    record(tmp_path)
    record(tmp_path, answered_by="gemini:gemini-3.5-flash-lite", reached_external=True, gpu_watts=None, seconds=3.0)
    record(tmp_path, reachable=False, answered_by="", caller="troubleshooting")
    text = unescape(client(tmp_path).get("/footprint/?lang=en").text)

    assert "3 calls, 2 of them answered: 1 on your machines, 1 at an outside provider, 1 without an answer" in text
    assert "Machine that answers, at home" in text and "Machine that answers, at a provider" in text
    assert "1 with the graphics card's power read during the call, 0 calculated" in text
    assert "<code>portal.chat</code>" in text and "<code>troubleshooting</code>" in text
    assert "gCO2e" in text or "mgCO2e" in text


def test_every_parameter_is_shown_with_its_origin(tmp_path: Path):
    text = unescape(client(tmp_path).get("/footprint/?lang=en").text)

    assert "Emission factor of electricity in France" in text
    assert "measured" in text and "published by the source" in text and "declared, to confirm" in text
    assert "Ember" in text and "RTE" in text and "Epoch AI" in text


def test_the_page_says_what_it_does_not_count_and_does_not_claim_conformity(tmp_path: Path):
    text = unescape(client(tmp_path).get("/footprint/?lang=en").text)

    assert "What is not counted" in text
    assert "abiotic resource depletion and primary energy" in text
    assert "not certified as conforming" in text
    assert "inspired by AFNOR SPEC 2314" in text


def test_the_page_is_in_french_too(tmp_path: Path):
    record(tmp_path)
    text = unescape(client(tmp_path).get("/footprint/?lang=fr").text)

    assert "Usage et empreinte" in text and "Ce qui n'est pas compté" in text
    assert "Charge permanente d'AIStack" in text


def test_no_word_of_a_question_can_be_on_the_page(tmp_path: Path):
    record(tmp_path, route="external_allowed; kind=question; chose qwen2.5:7b: stays inside")
    text = unescape(client(tmp_path).get("/footprint/?lang=fr").text)

    assert "chose qwen2.5:7b" not in text


def test_an_unreadable_declaration_is_said_not_hidden(tmp_path: Path, monkeypatch):
    def broken():
        raise ValueError("footprint.yml: parameter `grid_local` is missing")

    monkeypatch.setattr(footprint_screen, "load_footprint_yaml", broken)
    reply = client(tmp_path).get("/footprint/?lang=en")

    assert reply.status_code == 200
    assert "cannot be read" in reply.text and "grid_local" in reply.text


def test_the_page_is_not_served_on_the_public_port(tmp_path: Path):
    assert client(tmp_path, PUBLIC_PORT).get("/footprint/").status_code == 404


def test_the_page_asks_for_a_signed_in_person(tmp_path: Path):
    app = create_app(tmp_path, LISTENERS, LANGUAGES, WebPaths())
    reply = TestClient(app, base_url=f"http://testserver:{LAN_PORT}", follow_redirects=False).get("/footprint/")

    assert reply.status_code in (302, 303, 307, 401)
