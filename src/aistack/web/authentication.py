"""
Signing in and out (`ADR-0013`, 1.7 tranche 2).

Two routers, because the two ways in are not exposed alike:

- `router` (`PUBLIC`): `GET /login`, `GET /auth/callback` and
  `POST /logout` — OpenID Connect against Pocket ID, used on the public
  address; the redirect URI is the configured public one.
- `lan_router` (`LAN_ONLY`): `GET`/`POST /login/local` — the fallback
  administrator, never served on the public port.

Nothing is refused to an anonymous visitor in this tranche (§ 1). The
session is read once per request by `current_session`, and
`fill_session_marker` writes who is signed in into every HTML page the
application serves, generated ones included (§ 7).
"""

from __future__ import annotations

import logging
import os
import secrets
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse, Response

from aistack.authentication.definition import (
    DEFAULT_DEFINITION,
    AuthenticationDefinition,
    Credentials,
    credentials_from,
    load_authentication_yaml,
)
from aistack.authentication.local_admin import FailureWindow, verify_password
from aistack.authentication.oidc import Http, OidcClient, SignInError, UrllibHttp
from aistack.authentication.sessions import LOCAL, OIDC, Session, SessionStore
from aistack.i18n import LANGUAGE_COOKIE, LANGUAGE_PARAMETER
from aistack.i18n.web import PageLanguage, page_language
from aistack.renderers.nav import SESSION_MARKER
from aistack.renderers.text import escape_text
from aistack.web.exposure import LAN_ONLY, PUBLIC, arrival_port
from aistack.web.templating import templates

SESSION_COOKIE = "aistack_session"
CSRF_COOKIE = "aistack_csrf"
DEFAULT_NEXT = "/console.html"
LOCAL_SUBJECT = "local-admin"

# Why a sign-in was refused goes to the service's journal
# (`journalctl -u aistack-web`); the page says it in the reader's words.
log = logging.getLogger("aistack.web.authentication")

# Never 502 or 504: Cloudflare, in front of the public address, replaces
# those answers with its own page and the reader never sees why.
UNAVAILABLE = 503

router = APIRouter(dependencies=[PUBLIC])
lan_router = APIRouter(dependencies=[LAN_ONLY])


@dataclass
class Authentication:
    """Everything sign-in needs, built once by `create_app`."""

    definition: AuthenticationDefinition
    credentials: Credentials
    sessions: SessionStore
    oidc: OidcClient
    failures: FailureWindow = field(default_factory=FailureWindow)


def build_authentication(
    generated_dir: Path,
    environment: Mapping[str, str] | None = None,
    definition_path: Path = DEFAULT_DEFINITION,
    http: Http | None = None,
) -> Authentication:
    definition = load_authentication_yaml(definition_path)
    credentials = credentials_from(environment if environment is not None else os.environ, definition)

    return Authentication(
        definition=definition,
        credentials=credentials,
        sessions=SessionStore(
            generated_dir / "web" / "sessions.sqlite3",
            idle_seconds=definition.session_idle_hours * 3600,
            absolute_seconds=definition.session_absolute_days * 86400,
        ),
        oidc=OidcClient(definition, credentials, http if http is not None else UrllibHttp()),
    )


def _auth(request: Request) -> Authentication:
    authentication: Authentication = request.app.state.authentication
    return authentication


def _language(request: Request) -> PageLanguage:
    return page_language(
        request.query_params.get(LANGUAGE_PARAMETER),
        request.cookies.get(LANGUAGE_COOKIE),
        request.app.state.languages,
    )


def on_public_port(request: Request) -> bool:
    return arrival_port(request) == request.app.state.listeners.public_port


def current_session(request: Request) -> Session | None:
    """The signed-in person, read once per request."""

    if "aistack_session" not in request.scope:
        request.scope["aistack_session"] = _auth(request).sessions.get(
            request.cookies.get(SESSION_COOKIE)
        )
    session: Session | None = request.scope["aistack_session"]
    return session


def _safe_next(target: str | None) -> str:
    """A path on this site, never another one: `/x`, not `//host` or `http:`."""

    if not target or not target.startswith("/") or target.startswith("//") or "\\" in target:
        return DEFAULT_NEXT
    return target


def _message(request: Request, heading: str, message: str, status: int = 200, error: bool = False) -> Response:
    language = _language(request)
    return templates.TemplateResponse(
        request=request,
        name="auth/message.html",
        context={"heading": heading, "message": message, "error": error, **language.context()},
        status_code=status,
    )


def _signed_in(request: Request, response: Response, identifier: str) -> Response:
    response.set_cookie(
        SESSION_COOKIE,
        identifier,
        httponly=True,
        samesite="lax",
        path="/",
        secure=on_public_port(request),
        max_age=int(_auth(request).sessions.absolute_seconds),
    )
    return response


# --------------------------------------------------------------------
# OpenID Connect — the public address
# --------------------------------------------------------------------


@router.get("/login", include_in_schema=False)
def login(request: Request) -> Response:
    authentication = _auth(request)
    t = _language(request).t

    if not authentication.credentials.oidc_configured:
        return _message(request, t("auth.heading"), t("auth.error.not_configured"), UNAVAILABLE, error=True)

    try:
        url, state, pending = authentication.oidc.start(_safe_next(request.query_params.get("next")))
    except SignInError as error:
        log.warning("sign-in could not start: %s", error)
        return _message(request, t("auth.heading"), t(error.reason), UNAVAILABLE, error=True)

    authentication.sessions.remember(state, pending)
    return RedirectResponse(url, status_code=303)


@router.get("/auth/callback", include_in_schema=False)
def callback(request: Request) -> Response:
    authentication = _auth(request)
    t = _language(request).t
    parameters = request.query_params

    pending = authentication.sessions.take(parameters.get("state"))
    if pending is None:
        log.warning("sign-in callback for an unknown or expired attempt")
        return _message(request, t("auth.heading"), t("auth.error.unknown_attempt"), 400, error=True)

    if parameters.get("error"):
        log.warning("sign-in denied by the provider: %s", parameters.get("error"))
        return _message(request, t("auth.heading"), t("auth.error.denied"), 403, error=True)

    try:
        identity = authentication.oidc.finish(parameters.get("code", ""), parameters.get("iss"), pending)
    except SignInError as error:
        log.warning("sign-in refused: %s", error)
        return _message(request, t("auth.heading"), t(error.reason), 403, error=True)

    identifier = authentication.sessions.open(
        subject=identity.subject,
        name=identity.name,
        email=identity.email,
        groups=identity.groups,
        method=OIDC,
        id_token=identity.id_token,
    )
    return _signed_in(request, RedirectResponse(pending.next, status_code=303), identifier)


@router.post("/logout", include_in_schema=False)
def logout(request: Request, csrf: str = Form("")) -> Response:
    authentication = _auth(request)
    identifier = request.cookies.get(SESSION_COOKIE)
    session = current_session(request)

    if session is not None and not secrets.compare_digest(csrf, session.csrf):
        t = _language(request).t
        return _message(request, t("auth.heading"), t("auth.error.csrf"), 403, error=True)

    target = DEFAULT_NEXT
    if session is not None:
        authentication.sessions.close(identifier)
        if session.method == OIDC and authentication.credentials.oidc_configured:
            target = authentication.oidc.logout_url(session.id_token) or DEFAULT_NEXT

    response = RedirectResponse(target, status_code=303)
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response


# --------------------------------------------------------------------
# The fallback administrator — the LAN port only
# --------------------------------------------------------------------


def _local_form(request: Request, error: str = "", status: int = 200) -> Response:
    token = secrets.token_urlsafe(32)
    response = templates.TemplateResponse(
        request=request,
        name="auth/local.html",
        context={"csrf": token, "error": error, **_language(request).context()},
        status_code=status,
    )
    response.set_cookie(CSRF_COOKIE, token, httponly=True, samesite="strict", path="/login/local")
    return response


@lan_router.get("/login/local", include_in_schema=False)
def local_form(request: Request) -> Response:
    t = _language(request).t
    if not _auth(request).credentials.local_admin_hash:
        return _message(request, t("auth.local.heading"), t("auth.error.local_not_configured"), 503, error=True)
    return _local_form(request)


@lan_router.post("/login/local", include_in_schema=False)
def local_login(request: Request, password: str = Form(""), csrf: str = Form("")) -> Response:
    authentication = _auth(request)
    t = _language(request).t

    if not authentication.credentials.local_admin_hash:
        return _message(request, t("auth.local.heading"), t("auth.error.local_not_configured"), 503, error=True)

    expected = request.cookies.get(CSRF_COOKIE, "")
    if not expected or not secrets.compare_digest(csrf, expected):
        return _local_form(request, t("auth.error.csrf"), 403)

    if authentication.failures.locked():
        return _local_form(request, t("auth.error.locked"), 429)

    if not verify_password(password, authentication.credentials.local_admin_hash):
        authentication.failures.failed()
        return _local_form(request, t("auth.error.wrong_password"), 401)

    authentication.failures.succeeded()
    identifier = authentication.sessions.open(subject=LOCAL_SUBJECT, name=LOCAL_SUBJECT, method=LOCAL)
    response = _signed_in(request, RedirectResponse(DEFAULT_NEXT, status_code=303), identifier)
    response.delete_cookie(CSRF_COOKIE, path="/login/local")
    return response


# --------------------------------------------------------------------
# Who is signed in, on every page
# --------------------------------------------------------------------

_LINK = "color:#16335c;text-decoration:none;font-size:.85rem"
_BUTTON = (
    "font-size:.8rem;padding:.15rem .5rem;border:1px solid #dde4ed;border-radius:6px;"
    "background:#fff;color:#16335c;cursor:pointer"
)


def session_block(request: Request) -> str:
    """The person's name and a sign-out button, or the way to sign in
    on this listener: Pocket ID on the public port, the fallback
    administrator on the LAN port."""

    t = _language(request).t
    session = current_session(request)

    if session is None:
        if on_public_port(request):
            return (
                f'<a class="session-link" href="/login" style="{_LINK}" '
                f'title="{escape_text(t("auth.tooltip.login"))}">{escape_text(t("auth.login"))}</a>'
            )
        return (
            f'<a class="session-link" href="/login/local" style="{_LINK}" '
            f'title="{escape_text(t("auth.tooltip.login_local"))}">{escape_text(t("auth.login_local"))}</a>'
        )

    shown = t("auth.local.display") if session.method == LOCAL else session.name
    return (
        '<form class="session" method="post" action="/logout" '
        'style="display:inline-flex;align-items:center;gap:.4rem;margin:0">'
        f'<span class="session-user" style="font-size:.85rem" '
        f'title="{escape_text(t("auth.tooltip.signed_in_as", name=shown))}">{escape_text(shown)}</span>'
        f'<input type="hidden" name="csrf" value="{escape_text(session.csrf)}">'
        f'<button type="submit" style="{_BUTTON}" title="{escape_text(t("auth.tooltip.logout"))}">'
        f"{escape_text(t('auth.logout'))}</button></form>"
    )


def fill_session_marker(request: Request, body: bytes) -> bytes:
    marker = SESSION_MARKER.encode("ascii")
    if marker not in body:
        return body
    return body.replace(marker, session_block(request).encode("utf-8"))
