"""
Profiles and rights (`ADR-0014`): who may read and act, asked of every
route of the application as `aistack.web.server` builds it, then
Settings and signing in on the LAN.
"""

from __future__ import annotations

import re
import sqlite3
import urllib.parse
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from aistack.authentication.oidc import OidcClient
from aistack.authentication.sessions import LOCAL, OIDC, Session, SessionStore
from aistack.i18n import Language, Languages
from aistack.renderers.nav import SESSION_MARKER
from aistack.web.app import create_app
from aistack.web.authentication import ADMIN, SESSION_COOKIE, USER, Authentication, profile_of
from aistack.web.exposure import Listeners
from tests.unit.authentication_fake import CREDENTIALS, DEFINITION, ISSUER, FakeProvider
from tests.unit.web_signed_in import as_user, signed_in

PUBLIC_PORT = 8183
LAN_PORT = 8186
LISTENERS = Listeners(public_port=PUBLIC_PORT, lan_port=LAN_PORT)
LANGUAGES = Languages(reference="fr", available=(Language("fr", "Français"), Language("en", "English")))

# What an anonymous visitor may ask (ADR-0014 § 1, § 5).
ANYONE = {
    "/",
    "/index.html",
    "/console.html",
    "/settings",
    "/help",
    "/help/manual",
    "/setup",
    "/legal",
    "/license",
    "/login",
    "/auth/callback",
    "/login/local",
    # Docker's healthcheck (1.10): "ok", nothing else, LAN listener only.
    "/healthz",
    # The AI notice's question (2026-10-09): nothing but an empty list
    # without a session.
    "/notifications",
    # The console cards' pastilles (2026-10-10): nothing without a session.
    "/pending",
    # The installation assistant (ADR-0023 § 5): its installation token
    # answers for it, on the LAN only — tests/unit/web/test_setup_wizard.py.
    "/setup/open",
    "/setup/step",
    "/setup/step/x",
}
# Sign-in itself, whose own checks (CSRF, password) answer for it, and
# the installation assistant, whose token does.
SIGN_IN_ACTIONS = {"/logout", "/login/local", "/setup/step/x"}


def build(tmp_path: Path, provider: FakeProvider | None = None):
    for page in ("console", "architecture", "health"):
        html = f'<!doctype html><html lang="fr"><nav>{SESSION_MARKER}</nav><p>{page}</p></html>'
        (tmp_path / f"{page}.html").write_text(html, encoding="utf-8")
        (tmp_path / f"{page}.en.html").write_text(html, encoding="utf-8")
    auth = Authentication(
        definition=DEFINITION,
        credentials=CREDENTIALS,
        sessions=SessionStore(tmp_path / "web" / "sessions.sqlite3", 8 * 3600, 7 * 86400),
        oidc=OidcClient(DEFINITION, CREDENTIALS, provider or FakeProvider()),
        lan_base_url="http://GIGABYTE:8186",
    )
    # Every host-touching collaborator replaced: these tests ask the
    # rights, never Docker (measured 2026-10-03 on a laptop without it).
    return create_app(
        tmp_path,
        LISTENERS,
        LANGUAGES,
        auth=auth,
        network_tree=lambda: [],
        discover=lambda: (),
        syncthing=lambda definition: None,
        collect_findings=lambda: ((), ""),
    )


def client(app, port: int = LAN_PORT) -> TestClient:
    scheme = "https" if port == PUBLIC_PORT else "http"
    return TestClient(app, base_url=f"{scheme}://testserver:{port}", follow_redirects=False)


def routes(app, method: str) -> list[str]:
    found = []
    for prefix, router, _guard in app.state.routers:
        for route in router.routes:
            if method in route.methods:
                found.append(re.sub(r"\{[^}]+\}", "x", prefix + route.path))
    return sorted(set(found))


# --------------------------------------------------------------------
# The profile
# --------------------------------------------------------------------


def session(method: str = OIDC, groups: tuple[str, ...] = ()) -> Session:
    return Session(subject="s", name="n", email="", groups=groups, method=method, id_token="", csrf="c")


def test_the_profile_comes_from_the_group_or_the_fallback_account():
    assert profile_of(None, "aistack_admins") is None
    assert profile_of(session(groups=("family",)), "aistack_admins") == USER
    assert profile_of(session(groups=("aistack_admins",)), "aistack_admins") == ADMIN
    assert profile_of(session(method=LOCAL), "aistack_admins") == ADMIN
    # The display name is not the group's name.
    assert profile_of(session(groups=("aistack-admins",)), "aistack_admins") == USER


# --------------------------------------------------------------------
# Every route, anonymously, as a user, as an administrator
# --------------------------------------------------------------------


def test_signed_out_every_page_but_the_public_ones_leads_to_sign_in(tmp_path: Path):
    app = build(tmp_path)
    web = client(app)
    protected = [path for path in routes(app, "GET") if path not in ANYONE]

    assert len(protected) >= 15
    for path in protected:
        reply = web.get(path)
        assert reply.status_code == 303, path
        assert reply.headers["location"].startswith("/login?next="), path


def test_signed_out_no_action_runs(tmp_path: Path):
    app = build(tmp_path)
    web = client(app)

    for path in routes(app, "POST"):
        if path in SIGN_IN_ACTIONS:
            continue
        reply = web.post(path, data={"csrf": "x"})
        assert reply.status_code == 303 and reply.headers["location"].startswith("/login"), path


def test_a_user_reads_but_every_action_is_refused(tmp_path: Path):
    app = build(tmp_path)
    web = as_user(client(app))

    assert web.get("/priority/").status_code == 200
    for path in routes(app, "POST"):
        if path in SIGN_IN_ACTIONS:
            continue
        reply = web.post(path)
        assert reply.status_code == 403, path
        assert "aistack_admins" in reply.text, path


def test_an_action_without_the_session_s_token_is_refused_even_to_an_administrator(tmp_path: Path):
    app = build(tmp_path)
    web = signed_in(client(app))

    reply = web.post("/network-discovery/add", data={"csrf": "forged", "username": "pi"})

    assert reply.status_code == 403


def test_every_form_of_a_screen_carries_the_session_s_token(tmp_path: Path):
    app = build(tmp_path)
    web = signed_in(client(app))
    token = app.state.authentication.sessions.live()[0].csrf

    page = web.get("/network-discovery/").text

    forms = re.findall(r'<form[^>]*method="post"[^>]*>(.*?)</form>', page, re.S)
    assert forms
    for form in forms:
        assert f'name="csrf" value="{token}"' in form


def test_after_signing_in_the_reader_comes_back_to_the_page_asked(tmp_path: Path):
    reply = client(build(tmp_path)).get("/timemachine/ribbon?subject=x")

    assert reply.headers["location"] == "/login?next=" + urllib.parse.quote("/timemachine/ribbon?subject=x", safe="")


# --------------------------------------------------------------------
# Pocket ID on the LAN (ADR-0014 § 4)
# --------------------------------------------------------------------


def test_signing_in_on_the_lan_uses_the_lan_callback_and_a_plain_cookie(tmp_path: Path):
    provider = FakeProvider()
    app = build(tmp_path, provider)
    web = client(app, LAN_PORT)

    started = web.get("/login?next=/priority/")
    query = provider.authorize(started.headers["location"])
    assert query["redirect_uri"] == "http://GIGABYTE:8186/auth/callback"

    done = web.get(f"/auth/callback?code=the-code&state={query['state']}&iss={urllib.parse.quote(ISSUER)}")

    assert done.status_code == 303 and done.headers["location"] == "/priority/"
    cookie = next(c for c in web.cookies.jar if c.name == SESSION_COOKIE)
    assert not cookie.secure
    assert web.get("/priority/").status_code == 200
    (live,) = app.state.authentication.sessions.live()
    assert live.listener == "lan"

    token = re.search(r'name="csrf" value="([^"]+)"', web.get("/console.html").text)
    out = web.post("/logout", data={"csrf": token.group(1) if token else ""})
    after = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(out.headers["location"]).query))
    assert after["post_logout_redirect_uri"] == "http://GIGABYTE:8186/console.html"


def test_the_public_sign_in_keeps_the_public_callback(tmp_path: Path):
    provider = FakeProvider()
    web = client(build(tmp_path, provider), PUBLIC_PORT)

    query = provider.authorize(web.get("/login").headers["location"])

    assert query["redirect_uri"] == "https://aistack.persiaut-family.fr/auth/callback"


# --------------------------------------------------------------------
# Settings (ADR-0014 § 6)
# --------------------------------------------------------------------


def test_a_user_sees_their_profile_and_nothing_of_the_others(tmp_path: Path):
    app = build(tmp_path)
    signed_in(client(app), name="Someone Else")
    web = as_user(client(app))

    page = web.get("/settings?lang=en").text

    assert "My profile" in page and "Reader" in page and "User (read only)" in page
    assert "Open sessions" not in page and "Sign-in journal" not in page
    assert "Someone Else" not in page


def test_the_profile_says_where_the_session_was_opened_in_good_french(tmp_path: Path):
    web = signed_in(client(build(tmp_path), PUBLIC_PORT))

    page = web.get("/settings?lang=fr").text

    assert "sur l&#x27;adresse publique" in page or "sur l'adresse publique" in page
    assert "sur le adresse" not in page


def test_signed_out_settings_only_offers_the_language(tmp_path: Path):
    page = client(build(tmp_path)).get("/settings?lang=en").text

    assert "My profile" not in page and "<!--aistack:settings-->" not in page


def test_an_administrator_sees_the_sessions_and_closes_another_one(tmp_path: Path):
    app = build(tmp_path)
    other = signed_in(client(app), groups=(), name="Someone Else")
    admin = signed_in(client(app), name="The Admin")

    page = admin.get("/settings?lang=en").text
    assert "Open sessions" in page and "Someone Else" in page and "this session" in page
    target = next(s for s in app.state.authentication.sessions.live() if s.name == "Someone Else")
    assert f'name="session" value="{target.public_id}"' in page

    closed = admin.post("/settings/sessions/close", data={"session": target.public_id})

    assert closed.status_code == 303
    assert other.get("/priority/").status_code == 303  # signed out
    journal = admin.get("/settings?lang=en").text
    assert "Session closed by an administrator" in journal


def test_the_journal_records_sign_ins_and_refusals(tmp_path: Path):
    provider = FakeProvider(token_claims={"aud": "someone-else"})
    app = build(tmp_path, provider)
    web = client(app, PUBLIC_PORT)
    query = provider.authorize(web.get("/login").headers["location"])
    web.get(f"/auth/callback?code=the-code&state={query['state']}&iss={urllib.parse.quote(ISSUER)}")

    (entry,) = app.state.authentication.sessions.journal()

    assert entry.event == "refused"
    assert "invalid_token" in entry.detail and "audience" in entry.detail.lower()


def test_a_database_of_the_first_schema_is_rebuilt(tmp_path: Path):
    path = tmp_path / "sessions.sqlite3"
    old = sqlite3.connect(path)
    old.execute("CREATE TABLE sessions (id_hash TEXT PRIMARY KEY, subject TEXT)")
    old.execute("INSERT INTO sessions VALUES ('x', 'y')")
    old.commit()
    old.close()

    store = SessionStore(path, 3600, 86400)

    assert store.count() == 0
    assert store.get(store.open(subject="s", name="n", method=OIDC)) is not None


@pytest.mark.parametrize("port", [PUBLIC_PORT, LAN_PORT])
def test_the_console_stays_public(tmp_path: Path, port: int):
    assert client(build(tmp_path), port).get("/console.html").status_code == 200


@pytest.mark.parametrize("port", [PUBLIC_PORT, LAN_PORT])
def test_the_manual_is_public_in_both_languages_and_help_leads_to_it(tmp_path: Path, port: int):
    web = client(build(tmp_path), port)

    help_page = web.get("/help?lang=en").text
    assert 'href="/help/manual?lang=en"' in help_page

    for lang, heading, setup in (
        ("fr", "Manuel utilisateur d&#x27;AIStack", "Mise en route d&#x27;une nouvelle installation"),
        ("en", "AIStack user manual", "Setting up a new installation"),
    ):
        page = web.get(f"/help/manual?lang={lang}")
        assert page.status_code == 200
        text = page.text.replace("'", "&#x27;")
        assert heading in text and setup in text
        assert 'class="toc"' in page.text


def test_an_administrator_sees_the_disks_and_mounts_and_a_user_does_not(tmp_path: Path):
    from aistack.host.mounts import Mount, MountRow, Usage

    rows = [
        MountRow(Mount("/dev/sda2", "/", "ext4", False), Usage(100 * 2**30, 25 * 2**30), ("code", "generated")),
        MountRow(Mount("nas:/music", "/mnt/music", "nfs4", True), None, ()),
    ]
    app = build(tmp_path)
    app.state.storage = lambda generated_dir: rows

    page = signed_in(client(app), name="Admin").get("/settings?lang=en").text
    assert "Disks and mounts" in page
    assert "<code>/mnt/music</code>" in page and "not answering" in page and "read-only · network" in page
    assert "100.0 Gio" in page and "25.0 Gio (25 %)" in page
    assert "the code and its environment, the histories and generated pages" in page

    assert "Disks and mounts" not in as_user(client(app)).get("/settings?lang=en").text
