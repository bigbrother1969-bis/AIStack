"""
*Selection UI* — what music is materialised for the Android phone, and
whether Syncthing has carried it there (`ADR-0012`; the screen
`selection_ui` served on port 8181 until 2026-10-03). LAN only: saving
writes hard links under the declared target directory.

A thin adapter over `aistack.selection.screen`. The kernel, the
repository root and the Syncthing reader reach the routes through the
application (`create_app`), so a test replaces Syncthing and points the
definition at a temporary library.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from aistack.application.yaml import load_application_definition_yaml
from aistack.i18n import LANGUAGE_COOKIE, LANGUAGE_PARAMETER
from aistack.i18n.web import PageLanguage, page_language
from aistack.kernel.application import ApplicationDefinition
from aistack.selection.screen import page_context, save_and_materialise, status_message
from aistack.web.exposure import LAN_ONLY
from aistack.web.templating import templates

PREFIX = "/selection"

router = APIRouter(dependencies=[LAN_ONLY])


def _language(request: Request) -> PageLanguage:
    return page_language(
        request.query_params.get(LANGUAGE_PARAMETER),
        request.cookies.get(LANGUAGE_COOKIE),
        request.app.state.languages,
    )


def _definition(request: Request) -> ApplicationDefinition:
    return load_application_definition_yaml(request.app.state.paths.selection)


@router.get("", response_class=HTMLResponse, include_in_schema=False)
@router.get("/", response_class=HTMLResponse, include_in_schema=False)
def index(request: Request) -> Response:
    language = _language(request)
    state = request.app.state

    context = page_context(
        _definition(request), state.kernel, state.paths.repository_root, state.syncthing
    )
    context.update(
        base=PREFIX,
        status=request.query_params.get("status"),
        **language.context(),
    )

    response = templates.TemplateResponse(
        request=request, name="selection/index.html", context=context
    )

    if language.cookie is not None:
        response.headers.append("set-cookie", language.cookie)

    return response


@router.get("/syncthing-status", include_in_schema=False)
def syncthing_status(request: Request) -> dict[str, Any] | None:
    """
    The Syncthing half of the page alone, polled by the page every few
    seconds: the catalog scan and the dry-run materialisation behind the
    rest cost real time on a 2393-node library, and nothing about a
    phone sync over a VPN justifies redoing them to learn a percentage
    moved. `null` when this instance declares no Syncthing block.
    """

    status: dict[str, Any] | None = request.app.state.syncthing(_definition(request))

    return status


@router.post("/save", include_in_schema=False)
async def save(request: Request) -> RedirectResponse:
    form = await request.form()
    selected_ids = [str(value) for value in form.getlist("selected_ids")]
    state = request.app.state

    report, count = save_and_materialise(
        _definition(request), state.kernel, state.paths.repository_root, selected_ids
    )

    message = status_message(report, count, _language(request).t)

    return RedirectResponse(f"{PREFIX}/?status={quote(message)}", status_code=303)
