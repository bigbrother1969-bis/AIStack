"""Settings' Profiles section (`ADR-0034`, GP2): administrators only,
pre-assignment, profile change, revocation with an immediate session
cut, and the change journal."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from aistack.authentication.profiles import ADMIN, USER
from aistack.authentication.sessions import OIDC
from aistack.i18n import Language, Languages
from aistack.web.app import WebPaths, create_app
from aistack.web.exposure import Listeners
from tests.unit.web_signed_in import signed_in

LISTENERS = Listeners(public_port=8183, lan_port=8186)
LANGUAGES = Languages(reference="fr", available=(Language("fr", "Français"), Language("en", "English")))


def client(tmp_path: Path, port: int = 8186) -> TestClient:
    app = create_app(tmp_path, LISTENERS, LANGUAGES, WebPaths())
    return signed_in(TestClient(app, base_url=f"http://testserver:{port}", follow_redirects=False))


def csrf(web: TestClient) -> str:
    page = web.get("/settings?lang=en").text
    marker = 'name="csrf" value="'
    start = page.index(marker) + len(marker)
    return page[start : page.index('"', start)]


def open_session(web: TestClient, email: str, name: str = "Alex") -> None:
    """A second, non-admin session for `email`, so a revocation on it
    can be observed from the admin session's own test client."""

    sessions = web.app.state.authentication.sessions  # type: ignore[attr-defined]
    sessions.open(subject=f"sub-{name}", name=name, email=email, groups=(), method=OIDC)


def test_a_pre_assignment_is_visible_at_once(tmp_path: Path):
    web = client(tmp_path)
    reply = web.post(
        "/settings/profiles/assign",
        data={"csrf": csrf(web), "identifier": "alex@example.org", "profile": ADMIN},
    )

    assert reply.status_code == 303 and "profile=assigned" in reply.headers["location"]
    page = web.get("/settings?lang=en").text
    assert 'id="profiles"' in page
    assert "alex@example.org" in page


def test_an_identifier_is_case_folded(tmp_path: Path):
    web = client(tmp_path)
    web.post(
        "/settings/profiles/assign",
        data={"csrf": csrf(web), "identifier": "Alex@Example.ORG", "profile": ADMIN},
    )

    page = web.get("/settings?lang=en").text
    assert "alex@example.org" in page
    assert "Alex@Example.ORG" not in page


def test_changing_the_profile_replaces_it_not_adds_a_row(tmp_path: Path):
    web = client(tmp_path)
    token = csrf(web)
    web.post("/settings/profiles/assign", data={"csrf": token, "identifier": "alex@example.org", "profile": USER})
    web.post("/settings/profiles/assign", data={"csrf": token, "identifier": "alex@example.org", "profile": ADMIN})

    known = web.app.state.authentication.profiles.known()  # type: ignore[attr-defined]
    assert len(known) == 1 and known[0].profile == ADMIN

    page = web.get("/settings?lang=en").text
    assert f'<option value="{ADMIN}" selected>' in page  # the select carries the current value


def test_revoking_cuts_the_live_session_at_once(tmp_path: Path):
    web = client(tmp_path)
    open_session(web, "alex@example.org")
    token = csrf(web)

    reply = web.post("/settings/profiles/revoke", data={"csrf": token, "identifier": "alex@example.org"})

    assert reply.status_code == 303 and "profile=revoked" in reply.headers["location"]
    sessions = web.app.state.authentication.sessions  # type: ignore[attr-defined]
    assert all(live.email != "alex@example.org" for live in sessions.live())


def test_revoking_an_account_with_no_live_session_still_logs_the_change(tmp_path: Path):
    web = client(tmp_path)
    token = csrf(web)

    web.post("/settings/profiles/revoke", data={"csrf": token, "identifier": "nobody@example.org"})

    page = web.get("/settings?lang=en").text
    assert "nobody@example.org" in page
    assert "Revoked" in page


def test_an_empty_identifier_is_refused(tmp_path: Path):
    web = client(tmp_path)
    reply = web.post("/settings/profiles/assign", data={"csrf": csrf(web), "identifier": "", "profile": ADMIN})

    assert "profile=empty" in reply.headers["location"]


def test_the_journal_records_who_assigned_what(tmp_path: Path):
    web = client(tmp_path)
    web.post(
        "/settings/profiles/assign",
        data={"csrf": csrf(web), "identifier": "alex@example.org", "profile": USER},
    )

    page = web.get("/settings?lang=en").text
    assert "Tester" in page  # `signed_in()`'s own display name, recorded as the author


def test_nobody_signed_out_sees_or_changes_a_profile(tmp_path: Path):
    app = client(tmp_path).app
    anonymous = TestClient(app, base_url="http://testserver:8186", follow_redirects=False)

    assert 'id="profiles"' not in anonymous.get("/settings").text
    reply = anonymous.post("/settings/profiles/assign", data={"identifier": "alex@example.org", "profile": ADMIN})
    assert reply.status_code in (303, 401, 403)


def test_a_non_admin_signed_in_person_cannot_assign_a_profile(tmp_path: Path):
    from tests.unit.web_signed_in import as_user

    web = as_user(client(tmp_path))
    reply = web.post("/settings/profiles/assign", data={"identifier": "alex@example.org", "profile": ADMIN})

    assert reply.status_code in (303, 401, 403)
    assert 'id="profiles"' not in web.get("/settings").text
