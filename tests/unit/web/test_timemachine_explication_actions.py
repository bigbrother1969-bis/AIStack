"""
Writing, validating and discarding the why on the Time Machine's
Explication page (`ADR-0015`), through the application as
`aistack.web.server` builds it: forms for an administrator only, each
act one more version, a refusal said in the reader's language.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from aistack.explications.human import versions
from aistack.i18n import Language, Languages
from aistack.web.app import create_app
from aistack.web.exposure import Listeners
from tests.unit.timemachine_sample import build_sample_graph, sample_tree
from tests.unit.web_signed_in import as_user, signed_in

LISTENERS = Listeners(public_port=8183, lan_port=8186)
LANGUAGES = Languages(reference="fr", available=(Language("fr", "Français"), Language("en", "English")))


@pytest.fixture(scope="module")
def generated(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return build_sample_graph(tmp_path_factory.mktemp("generated"))


@pytest.fixture(autouse=True)
def wall_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    readings = (datetime(2026, 10, 4, 9, 0, 0, tzinfo=UTC) + timedelta(seconds=i) for i in range(1000))
    monkeypatch.setattr("aistack.generators.history.wall_clock", lambda: next(readings))


def client(generated: Path) -> TestClient:
    app = create_app(generated, LISTENERS, LANGUAGES, network_tree=sample_tree)
    return TestClient(app, base_url="http://testserver:8186", follow_redirects=False)


def page(subject: str) -> str:
    return f"/timemachine/explication?subject={quote(subject)}&lang=en"


def test_an_administrator_gets_the_three_forms_each_with_the_session_s_token(generated: Path):
    web = signed_in(client(generated))
    token = web.app.state.authentication.sessions.live()[0].csrf  # type: ignore[attr-defined]

    text = web.get(page("booklore_db")).text

    for action in ("write", "validate", "discard"):
        form = re.search(rf'<form method="post" action="/timemachine/explication/{action}">(.*?)</form>', text, re.S)
        assert form, action
        assert f'name="csrf" value="{token}"' in form.group(1)
    # The text to correct starts from the current version.
    assert "nightly scan" in re.search(r"<textarea[^>]*>(.*?)</textarea>", text, re.S).group(1)


def test_a_user_reads_the_versions_and_gets_no_form(generated: Path):
    text = as_user(client(generated)).get(page("booklore_db")).text

    assert "nightly scan" in text
    assert "<form method=\"post\"" not in text


def test_writing_records_a_declared_version_by_the_person(generated: Path):
    web = signed_in(client(generated), name="Fabrice")

    done = web.post("/timemachine/explication/write", data={"subject": "frigate", "text": "Because the NVR needs it.", "expected": "0"})

    assert done.status_code == 303
    assert done.headers["location"] == "/timemachine/explication?subject=frigate&done=written"
    (only,) = versions("frigate", generated / "explications")
    assert only.artifact.confidence == "Declared"
    assert only.artifact.source == "person:sub-Fabrice"
    shown = web.get(page("frigate") + "&done=written").text
    assert "Version recorded" in shown and "Fabrice" in shown


def test_validating_one_s_own_text_is_refused_with_the_reason(generated: Path):
    web = signed_in(client(generated), name="Author")
    web.post("/timemachine/explication/write", data={"subject": "immich", "text": "Mine.", "expected": "0"})

    refused = web.post("/timemachine/explication/validate", data={"subject": "immich", "expected": "1"})

    assert refused.headers["location"].endswith("refused=timemachine.explication.refused.own_text")
    assert "its validation belongs to someone else" in web.get(refused.headers["location"] + "&lang=en").text
    assert len(versions("immich", generated / "explications")) == 1


def test_the_author_is_not_offered_the_validation_of_their_own_text(generated: Path):
    web = signed_in(client(generated), name="Self")
    web.post("/timemachine/explication/write", data={"subject": "bazarr", "text": "My reason.", "expected": "0"})

    text = web.get(page("bazarr")).text

    assert 'action="/timemachine/explication/validate"' not in text
    assert "its validation belongs to someone else" in text
    # Someone else is offered it.
    assert 'action="/timemachine/explication/validate"' in signed_in(client(generated), name="Other").get(page("bazarr")).text


def test_another_administrator_validates_and_the_page_says_by_whom(generated: Path):
    signed_in(client(generated), name="Writer").post(
        "/timemachine/explication/write", data={"subject": "nextcloud", "text": "Theirs.", "expected": "0"}
    )
    other = signed_in(client(generated), name="Checker")

    assert other.post("/timemachine/explication/validate", data={"subject": "nextcloud", "expected": "1"}).status_code == 303

    text = other.get(page("nextcloud")).text
    assert "Validated by" in text and "Checker" in text
    # Nothing left to validate on the current version.
    assert 'action="/timemachine/explication/validate"' not in text


def test_discarding_without_a_reason_is_refused_then_with_one_is_kept(generated: Path):
    web = signed_in(client(generated))
    web.post("/timemachine/explication/write", data={"subject": "wordpress", "text": "Guess.", "expected": "0"})

    refused = web.post("/timemachine/explication/discard", data={"subject": "wordpress", "reason": "", "expected": "1"})
    assert refused.headers["location"].endswith("refused.no_reason")

    web.post("/timemachine/explication/discard", data={"subject": "wordpress", "reason": "Not the cause.", "expected": "1"})
    text = web.get(page("wordpress")).text
    assert "Not the cause." in text and "Guess." in text and "Discarded" in text


def test_an_act_on_a_page_that_is_out_of_date_answers_409(generated: Path):
    web = signed_in(client(generated))
    web.post("/timemachine/explication/write", data={"subject": "jellyfin", "text": "One.", "expected": "0"})

    stale = web.post("/timemachine/explication/write", data={"subject": "jellyfin", "text": "Two.", "expected": "0"})

    assert stale.status_code == 409
    assert "changed since the page was opened" in stale.text or "a changé depuis" in stale.text
    assert len(versions("jellyfin", generated / "explications")) == 1
