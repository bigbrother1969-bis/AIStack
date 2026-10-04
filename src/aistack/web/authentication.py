"""
Signing in, profiles and rights (`ADR-0013`, `ADR-0014`).

Two routers, because the two ways in are not exposed alike:

- `router` (`PUBLIC`, both listeners): `GET /login`, `GET /auth/callback`,
  `POST /logout` — OpenID Connect against Pocket ID, the redirect URI
  being the one of the listener the sign-in started on — and
  `POST /settings/sessions/close`, an administrator's action.
- `lan_router` (`LAN_ONLY`): `GET`/`POST /login/local` — the fallback
  administrator, never served on the public port.

Rights (`ADR-0014` § 1, § 2): a route declares what it needs next to its
exposure — `SIGNED_IN` to read, `ADMIN_ACTION` to change something (the
admin profile and the session's CSRF token). Without a session the
answer is a redirect to sign in; without the profile, a `403`.

`fill_markers` writes, into every HTML page the application serves, who
is signed in, each form's CSRF token and the Settings sections.
"""

from __future__ import annotations

import logging
import os
import secrets
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import quote, urlsplit

from fastapi import APIRouter, Depends, Form, Request
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
from aistack.authentication.sessions import (
    CLOSED_BY_ADMIN,
    LAN_LISTENER,
    LOCAL,
    LOCAL_FAILED,
    LOCAL_LOCKED,
    OIDC,
    PUBLIC_LISTENER,
    REFUSED,
    SIGNED_IN,
    SIGNED_OUT,
    Session,
    SessionStore,
)
from aistack.i18n import LANGUAGE_COOKIE, LANGUAGE_PARAMETER, Translator
from aistack.i18n.web import PageLanguage, page_language
from aistack.renderers.nav import CSRF_MARKER, SESSION_MARKER, SETTINGS_MARKER
from aistack.renderers.text import escape_text
from aistack.web.exposure import LAN_ONLY, PUBLIC, arrival_port
from aistack.web.templating import templates

SESSION_COOKIE = "aistack_session"
CSRF_COOKIE = "aistack_csrf"
DEFAULT_NEXT = "/console.html"
LOCAL_SUBJECT = "local-admin"

ADMIN = "admin"
USER = "user"

# Why a sign-in was refused goes to the service's journal
# (`journalctl -u aistack-web`) and to the sign-in journal in Settings;
# the page says it in the reader's words.
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
    # Where the LAN listener is reached (ADR-0014 § 4).
    lan_base_url: str = "http://GIGABYTE:8186"
    failures: FailureWindow = field(default_factory=FailureWindow)


def build_authentication(
    generated_dir: Path,
    lan_base_url: str,
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
        lan_base_url=lan_base_url,
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


def _listener(request: Request) -> str:
    return PUBLIC_LISTENER if on_public_port(request) else LAN_LISTENER


def current_session(request: Request) -> Session | None:
    """The signed-in person, read once per request."""

    if "aistack_session" not in request.scope:
        request.scope["aistack_session"] = _auth(request).sessions.get(
            request.cookies.get(SESSION_COOKIE)
        )
    session: Session | None = request.scope["aistack_session"]
    return session


def profile_of(session: Session | None, admin_group: str) -> str | None:
    """`admin`, `user`, or `None` for nobody (ADR-0014 § 1)."""

    if session is None:
        return None
    if session.method == LOCAL or admin_group in session.groups:
        return ADMIN
    return USER


def current_profile(request: Request) -> str | None:
    return profile_of(current_session(request), _auth(request).definition.admin_group)


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
# Rights — what a route declares it needs (ADR-0014 § 2, § 3)
# --------------------------------------------------------------------


class SignInRequired(Exception):
    """No session: the answer is a redirect to sign in."""

    def __init__(self, next_path: str) -> None:
        super().__init__(next_path)
        self.next_path = next_path


class Refused(Exception):
    """A session without the right: `403`, with the reason's i18n key."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def _came_from(request: Request) -> str:
    """Where to come back after signing in: the page asked, or — for an
    action — the page of this site the form was on."""

    if request.method in ("GET", "HEAD"):
        query = f"?{request.url.query}" if request.url.query else ""
        return request.url.path + query

    referer = urlsplit(request.headers.get("referer", ""))
    if referer.netloc and referer.netloc == request.headers.get("host"):
        return _safe_next(referer.path + (f"?{referer.query}" if referer.query else ""))
    return DEFAULT_NEXT


def require_signed_in(request: Request) -> None:
    if current_session(request) is None:
        raise SignInRequired(_came_from(request))


async def require_admin_action(request: Request) -> None:
    session = current_session(request)
    if session is None:
        raise SignInRequired(_came_from(request))
    if current_profile(request) != ADMIN:
        raise Refused("auth.forbidden.not_admin")

    form = await request.form()
    token = form.get("csrf")
    if not isinstance(token, str) or not secrets.compare_digest(token, session.csrf):
        raise Refused("auth.error.csrf")


SIGNED_IN_ONLY = Depends(require_signed_in)
ADMIN_ACTION = Depends(require_admin_action)


def answer_sign_in_required(request: Request, error: SignInRequired) -> Response:
    return RedirectResponse(f"/login?next={quote(_safe_next(error.next_path), safe='')}", status_code=303)


def answer_refused(request: Request, error: Refused) -> Response:
    t = _language(request).t
    return _message(request, t("auth.forbidden.heading"), t(error.reason), 403, error=True)


# --------------------------------------------------------------------
# OpenID Connect — both listeners
# --------------------------------------------------------------------


def _base_url(authentication: Authentication, listener: str) -> str:
    return authentication.definition.public_base_url if listener == PUBLIC_LISTENER else authentication.lan_base_url


@router.get("/login", include_in_schema=False)
def login(request: Request) -> Response:
    authentication = _auth(request)
    t = _language(request).t
    listener = _listener(request)

    if not authentication.credentials.oidc_configured:
        return _message(request, t("auth.heading"), t("auth.error.not_configured"), UNAVAILABLE, error=True)

    try:
        url, state, pending = authentication.oidc.start(
            _safe_next(request.query_params.get("next")),
            authentication.definition.redirect_uri_for(_base_url(authentication, listener)),
            listener,
        )
    except SignInError as error:
        log.warning("sign-in could not start: %s", error)
        authentication.sessions.record(REFUSED, method=OIDC, listener=listener, detail=str(error))
        return _message(request, t("auth.heading"), t(error.reason), UNAVAILABLE, error=True)

    authentication.sessions.remember(state, pending)
    return RedirectResponse(url, status_code=303)


@router.get("/auth/callback", include_in_schema=False)
def callback(request: Request) -> Response:
    authentication = _auth(request)
    t = _language(request).t
    parameters = request.query_params
    listener = _listener(request)

    pending = authentication.sessions.take(parameters.get("state"))
    if pending is None:
        log.warning("sign-in callback for an unknown or expired attempt")
        authentication.sessions.record(REFUSED, method=OIDC, listener=listener, detail="unknown attempt")
        return _message(request, t("auth.heading"), t("auth.error.unknown_attempt"), 400, error=True)

    if parameters.get("error"):
        log.warning("sign-in denied by the provider: %s", parameters.get("error"))
        authentication.sessions.record(
            REFUSED, method=OIDC, listener=listener, detail=f"provider: {parameters.get('error')}"
        )
        return _message(request, t("auth.heading"), t("auth.error.denied"), 403, error=True)

    try:
        identity = authentication.oidc.finish(parameters.get("code", ""), parameters.get("iss"), pending)
    except SignInError as error:
        log.warning("sign-in refused: %s", error)
        authentication.sessions.record(REFUSED, method=OIDC, listener=listener, detail=str(error))
        return _message(request, t("auth.heading"), t(error.reason), 403, error=True)

    identifier = authentication.sessions.open(
        subject=identity.subject,
        name=identity.name,
        email=identity.email,
        groups=identity.groups,
        method=OIDC,
        id_token=identity.id_token,
        listener=pending.listener,
    )
    authentication.sessions.record(SIGNED_IN, name=identity.name, method=OIDC, listener=pending.listener)
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
        authentication.sessions.record(
            SIGNED_OUT, name=session.name, method=session.method, listener=session.listener
        )
        if session.method == OIDC and authentication.credentials.oidc_configured:
            after = authentication.definition.after_logout_uri_for(_base_url(authentication, session.listener))
            target = authentication.oidc.logout_url(session.id_token, after) or DEFAULT_NEXT

    response = RedirectResponse(target, status_code=303)
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response


@router.post("/settings/sessions/close", include_in_schema=False, dependencies=[ADMIN_ACTION])
def close_session(request: Request, session: str = Form("")) -> Response:
    """An administrator closes someone's session (ADR-0014 § 6)."""

    authentication = _auth(request)
    closed = [s for s in authentication.sessions.live() if s.public_id == session]
    if closed and authentication.sessions.close_public(session):
        admin = current_session(request)
        authentication.sessions.record(
            CLOSED_BY_ADMIN,
            name=closed[0].name,
            method=closed[0].method,
            listener=closed[0].listener,
            detail=admin.name if admin else "",
        )
    return RedirectResponse("/settings", status_code=303)


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
        authentication.sessions.record(LOCAL_LOCKED, method=LOCAL, listener=LAN_LISTENER)
        return _local_form(request, t("auth.error.locked"), 429)

    if not verify_password(password, authentication.credentials.local_admin_hash):
        authentication.failures.failed()
        authentication.sessions.record(LOCAL_FAILED, method=LOCAL, listener=LAN_LISTENER)
        return _local_form(request, t("auth.error.wrong_password"), 401)

    authentication.failures.succeeded()
    identifier = authentication.sessions.open(
        subject=LOCAL_SUBJECT, name=LOCAL_SUBJECT, method=LOCAL, listener=LAN_LISTENER
    )
    authentication.sessions.record(SIGNED_IN, name=LOCAL_SUBJECT, method=LOCAL, listener=LAN_LISTENER)
    response = _signed_in(request, RedirectResponse(DEFAULT_NEXT, status_code=303), identifier)
    response.delete_cookie(CSRF_COOKIE, path="/login/local")
    return response


# --------------------------------------------------------------------
# What every page carries: who is signed in, the CSRF token, Settings
# --------------------------------------------------------------------

_LINK = "color:#16335c;text-decoration:none;font-size:.85rem"
_BUTTON = (
    "font-size:.8rem;padding:.15rem .5rem;border:1px solid #dde4ed;border-radius:6px;"
    "background:#fff;color:#16335c;cursor:pointer"
)


def _shown(session: Session, t: Translator) -> str:
    return t("auth.local.display") if session.method == LOCAL else session.name


def session_block(request: Request) -> str:
    """The person's name and a sign-out button, or the way to sign in:
    Pocket ID on both listeners, the fallback administrator on the LAN."""

    t = _language(request).t
    session = current_session(request)

    if session is None:
        link = (
            f'<a class="session-link" href="/login" style="{_LINK}" '
            f'title="{escape_text(t("auth.tooltip.login"))}">{escape_text(t("auth.login"))}</a>'
        )
        if on_public_port(request):
            return link
        return (
            f"{link} "
            f'<a class="session-link" href="/login/local" style="{_LINK};opacity:.7" '
            f'title="{escape_text(t("auth.tooltip.login_local"))}">{escape_text(t("auth.login_local"))}</a>'
        )

    shown = _shown(session, t)
    return (
        '<form class="session" method="post" action="/logout" '
        'style="display:inline-flex;align-items:center;gap:.4rem;margin:0">'
        f'<span class="session-user" style="font-size:.85rem" '
        f'title="{escape_text(t("auth.tooltip.signed_in_as", name=shown))}">{escape_text(shown)}</span>'
        f'<input type="hidden" name="csrf" value="{escape_text(session.csrf)}">'
        f'<button type="submit" style="{_BUTTON}" title="{escape_text(t("auth.tooltip.logout"))}">'
        f"{escape_text(t('auth.logout'))}</button></form>"
    )


def csrf_field(request: Request) -> str:
    session = current_session(request)
    if session is None:
        return ""
    return f'<input type="hidden" name="csrf" value="{escape_text(session.csrf)}">'


_EVENT_LABELS = {
    SIGNED_IN: "auth.journal.event.signed_in",
    SIGNED_OUT: "auth.journal.event.signed_out",
    REFUSED: "auth.journal.event.refused",
    LOCAL_FAILED: "auth.journal.event.local_failed",
    LOCAL_LOCKED: "auth.journal.event.local_locked",
    CLOSED_BY_ADMIN: "auth.journal.event.closed_by_admin",
}
_METHOD_LABELS = {OIDC: "auth.method.oidc", LOCAL: "auth.method.local", "": "auth.method.none"}
_LISTENER_LABELS = {
    PUBLIC_LISTENER: "auth.listener.public",
    LAN_LISTENER: "auth.listener.lan",
    "": "auth.listener.none",
}
# "on the public address" needs its own article in French ("sur
# l'adresse publique"), so the whole phrase is translated, not the noun.
_WHERE_LABELS = {
    PUBLIC_LISTENER: "auth.settings.where.public",
    LAN_LISTENER: "auth.settings.where.lan",
    "": "auth.settings.where.none",
}
_PROFILE_LABELS = {ADMIN: "auth.profile.admin", USER: "auth.profile.user"}


def _when(at: float) -> str:
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(at))


def _row(*cells: str) -> str:
    return "<tr>" + "".join(f"<td>{cell}</td>" for cell in cells) + "</tr>"


def _head(t: Translator, *keys: str) -> str:
    return "<tr>" + "".join(f"<th>{escape_text(t(key))}</th>" for key in keys) + "</tr>"


def settings_sections(request: Request) -> str:
    """My profile, for everyone signed in; open sessions and the sign-in
    journal, for an administrator (ADR-0014 § 6)."""

    session = current_session(request)
    if session is None:
        return ""

    t = _language(request).t
    authentication = _auth(request)
    sessions = authentication.sessions
    profile = current_profile(request) or USER
    groups = ", ".join(session.groups) or t("auth.settings.no_group")

    parts = [
        '<section class="auth-settings">',
        f'<h2>{escape_text(t("auth.settings.profile_heading"))}</h2>',
        "<table>",
        _row(escape_text(t("auth.settings.name")), escape_text(_shown(session, t))),
        _row(escape_text(t("auth.settings.email")), escape_text(session.email or "—")),
        _row(escape_text(t("auth.settings.profile")), escape_text(t(_PROFILE_LABELS[profile]))),
        _row(escape_text(t("auth.settings.groups")), escape_text(groups)),
        _row(
            escape_text(t("auth.settings.opened")),
            escape_text(
                t(
                    "auth.settings.opened_value",
                    when=_when(session.created),
                    method=t(_METHOD_LABELS[session.method]),
                    where=t(_WHERE_LABELS.get(session.listener, "auth.settings.where.none")),
                )
            ),
        ),
        _row(escape_text(t("auth.settings.ends")), escape_text(_when(sessions.ends_at(session)))),
        "</table>",
        "</section>",
    ]

    if profile == ADMIN:
        token = escape_text(session.csrf)
        parts += [
            '<section class="auth-settings">',
            f'<h2>{escape_text(t("auth.settings.sessions_heading"))}</h2>',
            "<table>",
            _head(
                t,
                "auth.settings.column.who",
                "auth.settings.column.method",
                "auth.settings.column.listener",
                "auth.settings.column.since",
                "auth.settings.column.last_seen",
                "auth.settings.column.action",
            ),
        ]
        for live in sessions.live():
            mine = live.public_id == session.public_id
            action = (
                escape_text(t("auth.settings.this_session"))
                if mine
                else (
                    '<form method="post" action="/settings/sessions/close" style="margin:0">'
                    f'<input type="hidden" name="csrf" value="{token}">'
                    f'<input type="hidden" name="session" value="{escape_text(live.public_id)}">'
                    f'<button type="submit" title="{escape_text(t("auth.tooltip.close_session", name=_shown(live, t)))}">'
                    f'{escape_text(t("auth.settings.close"))}</button></form>'
                )
            )
            parts.append(
                _row(
                    escape_text(_shown(live, t)),
                    escape_text(t(_METHOD_LABELS[live.method])),
                    escape_text(t(_LISTENER_LABELS[live.listener])),
                    escape_text(_when(live.created)),
                    escape_text(_when(live.last_seen)),
                    action,
                )
            )
        parts += ["</table>", "</section>"]

        parts += [
            '<section class="auth-settings">',
            f'<h2>{escape_text(t("auth.settings.journal_heading"))}</h2>',
        ]
        entries = sessions.journal()
        if not entries:
            parts.append(f'<p>{escape_text(t("auth.settings.journal_empty"))}</p>')
        else:
            parts += [
                "<table>",
                _head(
                    t,
                    "auth.settings.column.when",
                    "auth.settings.column.event",
                    "auth.settings.column.who",
                    "auth.settings.column.method",
                    "auth.settings.column.listener",
                    "auth.settings.column.detail",
                ),
            ]
            for entry in entries:
                who = t("auth.local.display") if entry.method == LOCAL else entry.name
                parts.append(
                    _row(
                        escape_text(_when(entry.at)),
                        escape_text(t(_EVENT_LABELS.get(entry.event, "auth.journal.event.refused"))),
                        escape_text(who or "—"),
                        escape_text(t(_METHOD_LABELS.get(entry.method, "auth.method.none"))),
                        escape_text(t(_LISTENER_LABELS.get(entry.listener, "auth.listener.none"))),
                        escape_text(entry.detail),
                    )
                )
            parts.append("</table>")
        parts.append("</section>")

        from aistack.web.storage import storage_section

        parts.append(storage_section(request, t))

    return "\n".join(parts)


def fill_markers(request: Request, body: bytes) -> bytes:
    """Who is signed in, each form's token and the Settings sections."""

    for marker, fill in (
        (SESSION_MARKER, session_block),
        (CSRF_MARKER, csrf_field),
        (SETTINGS_MARKER, settings_sections),
    ):
        encoded = marker.encode("ascii")
        if encoded in body:
            body = body.replace(encoded, fill(request).encode("utf-8"))
    return body
