"""
Signing in and out inside the web application (`ADR-0013`), against a
fake Pocket ID (`tests/unit/authentication_fake.py`).
"""

from __future__ import annotations

import re
import urllib.parse
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from aistack.authentication.local_admin import hash_password
from aistack.authentication.oidc import OidcClient
from aistack.authentication.sessions import SessionStore
from aistack.i18n import Language, Languages
from aistack.renderers.nav import SESSION_MARKER
from aistack.web.app import create_app
from aistack.web.authentication import SESSION_COOKIE, Authentication
from aistack.web.exposure import Listeners
from tests.unit.authentication_fake import CREDENTIALS, DEFINITION, ISSUER, FakeProvider

PUBLIC_PORT = 8183
LAN_PORT = 8186
LISTENERS = Listeners(public_port=PUBLIC_PORT, lan_port=LAN_PORT)
LANGUAGES = Languages(
    reference="fr",
    available=(Language("fr", "Français"), Language("en", "English")),
)
PASSWORD = "the fallback password"
LOCAL_HASH = hash_password(PASSWORD)


def build(tmp_path: Path, provider: FakeProvider, configured: bool = True, local: bool = True):
    for page in ("console", "architecture", "health"):
        html = f"<!doctype html><html lang=\"fr\"><nav>{SESSION_MARKER}</nav><p>{page}</p></html>"
        (tmp_path / f"{page}.html").write_text(html, encoding="utf-8")
        (tmp_path / f"{page}.en.html").write_text(html.replace('"fr"', '"en"'), encoding="utf-8")

    credentials = type(CREDENTIALS)(
        client_id=CREDENTIALS.client_id if configured else "",
        client_secret=CREDENTIALS.client_secret if configured else "",
        local_admin_hash=LOCAL_HASH if local else "",
    )
    auth = Authentication(
        definition=DEFINITION,
        credentials=credentials,
        sessions=SessionStore(tmp_path / "web" / "sessions.sqlite3", 8 * 3600, 7 * 86400),
        oidc=OidcClient(DEFINITION, credentials, provider),
    )
    return create_app(tmp_path, LISTENERS, LANGUAGES, auth=auth)


def client(app, port: int = PUBLIC_PORT) -> TestClient:
    scheme = "https" if port == PUBLIC_PORT else "http"
    return TestClient(app, base_url=f"{scheme}://testserver:{port}", follow_redirects=False)


def sign_in(web: TestClient, provider: FakeProvider, next_path: str = "") -> str:
    started = web.get("/login" + (f"?next={urllib.parse.quote(next_path)}" if next_path else ""))
    assert started.status_code == 303
    query = provider.authorize(started.headers["location"])
    done = web.get(f"/auth/callback?code=the-code&state={query['state']}&iss={urllib.parse.quote(ISSUER)}")
    assert done.status_code == 303, done.text
    return done.headers["location"]


def test_an_anonymous_visitor_sees_every_page_and_a_sign_in_link(tmp_path: Path):
    web = client(build(tmp_path, FakeProvider()))

    page = web.get("/console.html?lang=en")

    assert page.status_code == 200
    assert SESSION_MARKER not in page.text
    assert 'href="/login"' in page.text and "Sign in" in page.text


def test_signing_in_opens_a_secure_session_and_names_the_person(tmp_path: Path):
    provider = FakeProvider()
    web = client(build(tmp_path, provider))

    location = sign_in(web, provider, "/health.html")

    assert location == "/health.html"
    cookie = next(c for c in web.cookies.jar if c.name == SESSION_COOKIE)
    assert cookie.secure
    page = web.get("/console.html?lang=en").text
    assert "Fabrice Persiaut" in page
    assert 'action="/logout"' in page and 'title="Signed in as Fabrice Persiaut"' in page


def test_the_redirect_after_sign_in_stays_on_this_site(tmp_path: Path):
    provider = FakeProvider()
    web = client(build(tmp_path, provider))

    for target in ("//evil.example/x", "https://evil.example", "/\\evil"):
        assert sign_in(web, provider, target) == "/console.html"


def test_a_callback_for_an_unknown_or_replayed_attempt_is_refused(tmp_path: Path):
    provider = FakeProvider()
    web = client(build(tmp_path, provider))
    started = web.get("/login")
    state = provider.authorize(started.headers["location"])["state"]
    callback = f"/auth/callback?code=the-code&state={state}&iss={urllib.parse.quote(ISSUER)}"

    assert web.get(callback).status_code == 303
    replayed = web.get(callback + "&lang=en")
    assert replayed.status_code == 400 and "unknown or has expired" in replayed.text
    assert web.get("/auth/callback?code=x&state=forged").status_code == 400


def test_a_token_that_fails_verification_opens_no_session(tmp_path: Path):
    provider = FakeProvider(token_claims={"aud": "someone-else"})
    app = build(tmp_path, provider)
    web = client(app)
    started = web.get("/login")
    state = provider.authorize(started.headers["location"])["state"]

    refused = web.get(f"/auth/callback?code=the-code&state={state}&iss={urllib.parse.quote(ISSUER)}&lang=en")

    assert refused.status_code == 403 and "could not be verified" in refused.text
    assert app.state.authentication.sessions.count() == 0


def test_a_denied_sign_in_says_so(tmp_path: Path):
    provider = FakeProvider()
    web = client(build(tmp_path, provider))
    state = provider.authorize(web.get("/login").headers["location"])["state"]

    assert web.get(f"/auth/callback?error=access_denied&state={state}").status_code == 403


def test_signing_out_needs_the_session_token_and_ends_both_sessions(tmp_path: Path):
    provider = FakeProvider()
    app = build(tmp_path, provider)
    web = client(app)
    sign_in(web, provider)
    token = re.search(r'name="csrf" value="([^"]+)"', web.get("/console.html").text)

    assert web.post("/logout", data={"csrf": "forged"}).status_code == 403
    assert app.state.authentication.sessions.count() == 1

    out = web.post("/logout", data={"csrf": token.group(1) if token else ""})

    assert out.status_code == 303
    assert out.headers["location"].startswith(f"{ISSUER}/api/oidc/end-session?")
    assert app.state.authentication.sessions.count() == 0
    assert 'href="/login"' in web.get("/console.html").text


def test_without_a_client_sign_in_says_it_is_not_configured(tmp_path: Path):
    web = client(build(tmp_path, FakeProvider(), configured=False))

    reply = web.get("/login?lang=en")

    assert reply.status_code == 503 and "not configured" in reply.text
    assert web.get("/console.html").status_code == 200


def test_an_unreachable_provider_is_said_so(tmp_path: Path):
    web = client(build(tmp_path, FakeProvider(down=True)))

    assert web.get("/login?lang=en").status_code == 502


# -- the fallback administrator --------------------------------------


def local_csrf(web: TestClient) -> str:
    form = web.get("/login/local")
    assert form.status_code == 200
    found = re.search(r'name="csrf" value="([^"]+)"', form.text)
    assert found
    return found.group(1)


def test_the_fallback_form_does_not_exist_on_the_public_port(tmp_path: Path):
    web = client(build(tmp_path, FakeProvider()))

    assert web.get("/login/local").status_code == 404
    assert web.post("/login/local", data={"password": PASSWORD}).status_code == 404


def test_the_fallback_administrator_signs_in_on_the_lan(tmp_path: Path):
    app = build(tmp_path, FakeProvider())
    web = client(app, LAN_PORT)

    assert 'href="/login/local"' in web.get("/console.html").text
    done = web.post("/login/local", data={"password": PASSWORD, "csrf": local_csrf(web)})

    assert done.status_code == 303
    cookie = next(c for c in web.cookies.jar if c.name == SESSION_COOKIE)
    assert not cookie.secure  # plain HTTP on the LAN port
    page = web.get("/console.html?lang=en").text
    assert "Fallback administrator" in page and 'action="/logout"' in page


def test_the_fallback_form_needs_its_token(tmp_path: Path):
    web = client(build(tmp_path, FakeProvider()), LAN_PORT)
    local_csrf(web)

    assert web.post("/login/local", data={"password": PASSWORD, "csrf": "forged"}).status_code == 403


def test_five_wrong_passwords_lock_the_fallback_form(tmp_path: Path):
    web = client(build(tmp_path, FakeProvider()), LAN_PORT)

    for _ in range(5):
        assert web.post("/login/local", data={"password": "wrong", "csrf": local_csrf(web)}).status_code == 401
    locked = web.post("/login/local", data={"password": PASSWORD, "csrf": local_csrf(web)})

    assert locked.status_code == 429


def test_without_a_hash_the_fallback_is_not_configured(tmp_path: Path):
    web = client(build(tmp_path, FakeProvider(), local=False), LAN_PORT)

    assert web.get("/login/local").status_code == 503


@pytest.mark.parametrize("port", [PUBLIC_PORT, LAN_PORT])
def test_a_head_request_is_not_rewritten(tmp_path: Path, port: int):
    web = client(build(tmp_path, FakeProvider()), port)

    assert web.head("/console.html").status_code == 200
