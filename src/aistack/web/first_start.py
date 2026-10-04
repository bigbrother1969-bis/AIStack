"""
The guided first start (`ADR-0017` § 4): a page, `/setup`, saying what a
new installation still has to declare, and a link to it at the top of
every page while something required is missing.

Public, like the console: on a new installation nobody can sign in yet —
signing in is one of the things to declare. It shows declaration file
names, variable names and the values in use, never a secret.

What is missing is measured once, when the application is created: the
declarations are read at start and the secrets come from the process's
environment, so nothing can change before the next restart.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, Response

from aistack.config import config_dir
from aistack.i18n import LANGUAGE_COOKIE, LANGUAGE_PARAMETER
from aistack.i18n.web import PageLanguage, page_language
from aistack.instance.first_start import (
    AUTHENTICATION,
    FALLBACK_SECRET,
    FIRST_DECLARATIONS,
    INSTANCE,
    SIGN_IN_SECRETS,
    Pending,
    needs_setup,
    pending,
)
from aistack.renderers.console.pages import MANUAL_PATH
from aistack.renderers.nav import PAGE_NAV_STYLE, render_page_nav
from aistack.renderers.text import escape_text
from aistack.web.exposure import PUBLIC
from aistack.web.templating import templates

SETUP_PATH = "/setup"

router = APIRouter(dependencies=[PUBLIC])

# Literal keys, so the catalog test sees every one of them.
HEADINGS = {
    INSTANCE: "first_start.item.instance.heading",
    AUTHENTICATION: "first_start.item.authentication.heading",
    SIGN_IN_SECRETS: "first_start.item.sign_in_secrets.heading",
    FALLBACK_SECRET: "first_start.item.fallback_secret.heading",
}
TEXTS = {
    INSTANCE: "first_start.item.instance.text",
    AUTHENTICATION: "first_start.item.authentication.text",
    SIGN_IN_SECRETS: "first_start.item.sign_in_secrets.text",
    FALLBACK_SECRET: "first_start.item.fallback_secret.text",
}

_BADGE = (
    "display:inline-block;padding:.2rem .6rem;border-radius:999px;font-size:.8rem;"
    "font-weight:600;background:#fff1cc;color:#7d4e00;border:1px solid #e8c766;text-decoration:none"
)


def measured(authentication: object) -> list[Pending]:
    """What the application being created still lacks."""

    credentials = authentication.credentials  # type: ignore[attr-defined]
    return pending(
        config_dir(),
        client_id=credentials.client_id,
        client_secret=credentials.client_secret,
        local_admin_hash=credentials.local_admin_hash,
    )


def _language(request: Request) -> PageLanguage:
    return page_language(
        request.query_params.get(LANGUAGE_PARAMETER),
        request.cookies.get(LANGUAGE_COOKIE),
        request.app.state.languages,
    )


def badge(request: Request) -> str:
    """The link to `/setup`, while something required is missing."""

    if not needs_setup(request.app.state.first_start):
        return ""
    t = _language(request).t
    return (
        f'<a class="setup-link" href="{SETUP_PATH}?lang={t.lang}" style="{_BADGE}" '
        f'title="{escape_text(t("first_start.tooltip.badge"))}">'
        f'{escape_text(t("first_start.badge"))}</a> '
    )


def _where(name: str) -> str:
    directory = config_dir()
    return f"{directory}/{name}" if directory is not None else name


def _values(request: Request, key: str, missing: str) -> list[tuple[str, str]]:
    """What is in use today, for the declaration `key` names."""

    if key == INSTANCE:
        config = request.app.state.instance_config
        return [("lan_hostname", config.lan_hostname)] + [
            (f"service_ports.{service}", str(port)) for service, port in sorted(config.service_ports.items())
        ] + [("phase", config.phase)]
    definition = request.app.state.authentication.definition
    if key == AUTHENTICATION:
        return [
            ("issuer", definition.issuer),
            ("public_base_url", definition.public_base_url),
            ("admin_group", definition.admin_group),
        ]
    if key == SIGN_IN_SECRETS:
        # Only the names: a secret present is never shown, and an item
        # is listed here because one is missing.
        return [(definition.client_id_env, missing), (definition.client_secret_env, missing)]
    return [(definition.local_admin_env, missing)]


def _file(key: str) -> str:
    return _where(FIRST_DECLARATIONS[key]) if key in FIRST_DECLARATIONS else ".env.web"


@router.get(SETUP_PATH, response_class=HTMLResponse, include_in_schema=False)
def setup(request: Request) -> Response:
    language = _language(request)
    t = language.t
    items = [
        {
            "heading": t(HEADINGS[item.key]),
            "text": t(TEXTS[item.key]),
            "file": _file(item.key),
            "in_use": _values(request, item.key, t("first_start.missing")),
            "required": item.required,
        }
        for item in request.app.state.first_start
    ]
    response = templates.TemplateResponse(
        request=request,
        name="first_start/index.html",
        context={
            "items": items,
            "needs_setup": needs_setup(request.app.state.first_start),
            "in_container": config_dir() is not None,
            "manual": f"{MANUAL_PATH}?lang={t.lang}#{t('first_start.manual_anchor')}",
            "page_nav_style": PAGE_NAV_STYLE,
            "page_nav": render_page_nav(t, request.app.state.languages, language.lang),
            **language.context(),
        },
    )
    if language.cookie is not None:
        response.headers.append("set-cookie", language.cookie)
    return response
