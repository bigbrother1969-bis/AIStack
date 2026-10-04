from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from aistack.i18n import (
    LANGUAGE_PARAMETER,
    Languages,
    default_languages,
    language_cookie_header,
    negotiate_language,
    read_cookie,
    translator_for,
)
from aistack.i18n.pages import page_file
from aistack.console.identity import load_console_identity
from aistack.renderers.console.pages import (
    HELP_PATH,
    LEGAL_PATH,
    LICENSE_PATH,
    MANUAL_PATH,
    render_help_html,
    render_manual_html,
    render_legal_html,
    render_license_html,
)
from aistack.renderers.console.settings import render_settings_html
from aistack.renderers.text import escape_text

# ADR-0010 § 5, revised by ADR-0012 (2026-10-02). The console was a
# directory served by the standard library's `http.server`
# (`run_console.sh`, `PLAN-J11` § 4), then, from 2026-09-27, a
# standard-library server of its own so a page could carry a language.
# Since ADR-0012 it is one router of AIStack's single web application
# (`aistack.web.console`), and this module keeps what was always the
# whole of it: `respond`, a pure function of the request line, its
# cookie and the generated directory. The router only adapts it.
#
# **Three generated pages and Settings, nothing else.** The same
# closed list `PUBLIC_DIR` used to expose (`aistack.cli.console_render`
# `_SERVED_ARTIFACTS`): `reports/generated/` also holds internal JSON
# catalogs and each artifact's own `history/`, and no path outside this
# list is ever mapped to a file — a request cannot name one.
PAGES = ("console.html", "architecture.html", "health.html")
SETTINGS_PATH = "/settings"

# The three reading pages the console's left column links to
# (2026-10-03), rendered per request like Settings: help, legal
# notice, licence and sources.
READING_PATHS = (HELP_PATH, MANUAL_PATH, LEGAL_PATH, LICENSE_PATH)


@dataclass(frozen=True)
class Response:
    """What one request is answered with — built purely, sent by the handler."""

    status: int
    body: bytes = b""
    headers: tuple[tuple[str, str], ...] = field(default_factory=tuple)


def respond(
    method: str,
    target: str,
    cookie_header: str | None,
    generated_dir: Path,
    languages: Languages | None = None,
) -> Response:
    """
    Answer one request — the whole server, as a pure function of the
    request line, its cookie and the generated directory, so every
    route is tested without opening a socket.

    The language is negotiated once (ADR-0010 § 3: `?lang=`, then the
    cookie, then the reference) and a response to a request that named
    a language sets the cookie, whatever the route — following a
    language link and submitting the Settings form are one mechanism.

    **A page not generated in the chosen language is served in the
    reference language rather than refused** — `architecture_render`
    and `health_render` run on their own schedule, and a page one of
    them has not yet regenerated since a language was added is still
    worth reading. A page not generated at all is a 404 that names it.
    """

    declared = languages if languages is not None else default_languages()
    parts = urlsplit(target)
    query = parse_qs(parts.query)
    requested = query.get(LANGUAGE_PARAMETER, [None])[0]
    choice = negotiate_language(requested, read_cookie(cookie_header), declared)
    remember = (
        (("Set-Cookie", language_cookie_header(choice.lang)),) if choice.remember else ()
    )

    path = parts.path

    if path in ("/", "/index.html"):
        location = "/console.html"

        if choice.remember:
            location += f"?{LANGUAGE_PARAMETER}={choice.lang}"

        return Response(status=302, headers=(("Location", location), *remember))

    if path == SETTINGS_PATH:
        html = render_settings_html(choice.lang, declared, saved=choice.remember)
        return _html(200, html, remember, method)

    if path == HELP_PATH:
        return _html(200, render_help_html(choice.lang, declared), remember, method)

    if path == MANUAL_PATH:
        return _html(200, render_manual_html(choice.lang, declared), remember, method)

    if path in (LEGAL_PATH, LICENSE_PATH):
        identity = load_console_identity(lang=choice.lang, languages=declared)
        render = render_legal_html if path == LEGAL_PATH else render_license_html
        return _html(200, render(identity, choice.lang, declared), remember, method)

    page = path.lstrip("/")

    if page in PAGES:
        localized = page_file(generated_dir, page, choice.lang, declared.reference)
        reference = generated_dir / page

        for candidate in (localized, reference):
            if candidate.is_file():
                return _html(200, candidate.read_text(encoding="utf-8"), remember, method)

        return _html(
            404,
            _message_page(choice.lang, "server.not_generated_title", "server.not_generated", page),
            remember,
            method,
        )

    return _html(
        404,
        _message_page(choice.lang, "server.not_found_title", "server.not_found", ""),
        remember,
        method,
    )


def _html(
    status: int,
    html: str,
    extra: tuple[tuple[str, str], ...],
    method: str,
) -> Response:
    body = html.encode("utf-8")

    headers = (
        ("Content-Type", "text/html; charset=utf-8"),
        ("Content-Length", str(len(body))),
        # The same URL answers in two languages: no cache may keep one
        # language's copy for the other's visitor.
        ("Cache-Control", "no-cache"),
        ("Vary", "Cookie"),
        ("X-Content-Type-Options", "nosniff"),
        ("Referrer-Policy", "same-origin"),
        *extra,
    )

    return Response(status=status, body=b"" if method == "HEAD" else body, headers=headers)


def _message_page(lang: str, title_key: str, message_key: str, page: str) -> str:
    t = translator_for(lang)
    title = escape_text(t(title_key))
    message = escape_text(t(message_key, page=page) if page else t(message_key))

    return f"""<!doctype html>
<html lang="{t.lang}">
<head>
<meta charset="utf-8">
<title>AIStack — {title}</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; max-width: 640px; margin: 3rem auto; color: #1f2933; background: #f7f9fc; padding: 0 1rem">
<h1 style="font-family: Georgia, 'Times New Roman', Times, serif; font-weight: normal; color: #16335c">{title}</h1>
<p>{message}</p>
<p><a href="/console.html" style="color: #16335c">{escape_text(t("server.back"))}</a></p>
</body>
</html>
"""
