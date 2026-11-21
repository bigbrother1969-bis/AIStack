"""*Moteurs IA* inside AIStack's web application (ADR-0029 § 8): a reading screen, LAN only, over the journal of AI calls."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from tests.unit.web_signed_in import signed_in

from aistack.ai_runtime import call_journal
from aistack.ai_runtime.call_journal import Call
from aistack.i18n import Language, Languages
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
        at="2026-11-21T09:39:49+00:00", caller="troubleshooting", operation="reason", language="fr",
        answered_by="anthropic:claude-sonnet-5-5", reached_external=True, reachable=True, seconds=5.8,
        set_aside="", policy_class="external_allowed", policy_differs=False,
        route="external_allowed; kind=diagnosis; chose anthropic: long reasoning over several facts at once",
        kind="diagnosis",
    )
    call_journal.append(tmp_path / "ai-calls", Call(**{**base, **more}))


def test_before_any_question_the_page_says_the_journal_is_empty(tmp_path: Path):
    reply = client(tmp_path).get("/ai-engines/?lang=en")

    assert reply.status_code == 200
    assert "The journal is empty" in reply.text and "No call yet." in reply.text
    assert 'href="/console.html?lang=en"' in reply.text


def test_the_page_lists_the_engines_the_policy_and_the_table_with_their_reasons(tmp_path: Path):
    text = client(tmp_path).get("/ai-engines?lang=en").text

    for name in ("Gemini", "ChatGPT", "Claude"):
        assert name in text
    assert "not declared" in text
    assert "troubleshooting" in text and "internal only" in text
    assert "diagnosis" in text and "long reasoning over several facts at once" in text


def test_the_page_shows_what_each_call_decided_and_why_newest_first(tmp_path: Path):
    record(tmp_path, at="2026-11-21T09:39:49+00:00")
    record(
        tmp_path, at="2026-11-21T09:40:07+00:00", operation="recommend", kind="recommendation",
        route="external_allowed; kind=recommendation; chose anthropic: the steps and commands you will run: precision before speed",
    )

    text = client(tmp_path).get("/ai-engines/?lang=en").text

    assert "2 call(s) in the journal, 2 of them sent to an outside engine" in text
    assert text.index("09:40:07") < text.index("09:39:49")
    assert "precision before speed" in text and "anthropic:claude-sonnet-5-5" in text


def test_a_silent_engine_and_the_reason_it_gave_are_shown(tmp_path: Path):
    record(
        tmp_path, answered_by="gemini:g-x (Claude: refused)",
        route="external_allowed; kind=diagnosis; chose gemini: fast; silent: anthropic (Claude refused the request with status 400)",
    )

    text = client(tmp_path).get("/ai-engines/?lang=en").text

    assert "Claude refused the request with status 400" in text
    assert "1 call(s) where a first engine stayed silent" in text


def test_a_key_is_never_on_the_page(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("AISTACK_GEMINI_API_KEY", "SECRET-VALUE-123")

    assert "SECRET-VALUE-123" not in client(tmp_path).get("/ai-engines/?lang=fr").text


def test_the_page_is_in_french_too(tmp_path: Path):
    assert "Ce qui a été demandé" in client(tmp_path).get("/ai-engines/?lang=fr").text


def test_the_reasons_of_the_table_and_of_the_choices_are_said_in_french_on_the_french_page(tmp_path: Path):
    record(
        tmp_path, at="2026-11-21T09:40:07+00:00", operation="recommend", kind="recommendation",
        route="external_allowed; kind=recommendation; chose anthropic: the steps and commands you will run: precision before speed",
    )

    text = client(tmp_path).get("/ai-engines/?lang=fr").text

    assert "raisonne longuement sur plusieurs faits à la fois" in text
    assert "la précision avant la vitesse" in text
    assert "precision before speed" not in text


def test_nothing_answers_on_the_public_port(tmp_path: Path):
    assert client(tmp_path, PUBLIC_PORT).get("/ai-engines/").status_code == 404


def test_the_page_says_when_blocks_of_the_policy_come_from_the_shipped_file(tmp_path: Path, monkeypatch):
    config = tmp_path / "config"
    config.mkdir()
    (config / "ai_policy.yml").write_text("callers:\n  troubleshooting: external_allowed\n", encoding="utf-8")
    monkeypatch.setenv("AISTACK_CONFIG_DIR", str(config))

    text = client(tmp_path).get("/ai-engines/?lang=en").text

    assert "does not hold: kinds, preferences" in text
    assert "long reasoning over several facts at once" in text


def test_the_page_says_nothing_of_it_when_the_policy_is_whole(tmp_path: Path):
    text = client(tmp_path).get("/ai-engines/?lang=en").text

    assert "does not hold" not in text
