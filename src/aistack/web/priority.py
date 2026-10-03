"""
*Priorité CPU* — which containers are boosted, throttled or left alone
(`ADR-0012`; the screen `priority_ui` served on port 8182 until
2026-10-03). LAN only, like every screen that acts on the host.

A thin adapter: the join of Docker's containers with the governed
definition, and the definition the form describes, are
`aistack.priority.screen`, tested on their own. What Docker reports
reaches the route through `app.state.discover_containers`, so a test
replaces it; the route never builds a provider itself.
"""

from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from aistack.i18n import LANGUAGE_COOKIE, LANGUAGE_PARAMETER
from aistack.i18n.web import PageLanguage, page_language
from aistack.priority.screen import definition_from_form, priority_rows
from aistack.priority.yaml import load_resource_priority_yaml, save_resource_priority_yaml
from aistack.web.authentication import ADMIN_ACTION, SIGNED_IN_ONLY
from aistack.web.exposure import LAN_ONLY
from aistack.web.templating import templates

PREFIX = "/priority"

router = APIRouter(dependencies=[LAN_ONLY, SIGNED_IN_ONLY])


def _language(request: Request) -> PageLanguage:
    return page_language(
        request.query_params.get(LANGUAGE_PARAMETER),
        request.cookies.get(LANGUAGE_COOKIE),
        request.app.state.languages,
    )


@router.get("", response_class=HTMLResponse, include_in_schema=False)
@router.get("/", response_class=HTMLResponse, include_in_schema=False)
def index(request: Request) -> Response:
    language = _language(request)
    definition = load_resource_priority_yaml(request.app.state.paths.resource_priority)

    context: dict[str, object] = {
        "base": PREFIX,
        "rows": priority_rows(definition, request.app.state.discover_containers()),
        "unlimited_cpus": definition.unlimited_cpus,
        "grace_seconds": definition.grace_seconds,
        "default_throttled_cpus": definition.background.default_throttled_cpus,
        "status": request.query_params.get("status"),
        **language.context(),
    }

    response = templates.TemplateResponse(
        request=request, name="priority/index.html", context=context
    )

    if language.cookie is not None:
        response.headers.append("set-cookie", language.cookie)

    return response


@router.post("/save", include_in_schema=False, dependencies=[ADMIN_ACTION])
async def save(request: Request) -> RedirectResponse:
    """Rewrite the governed definition from the form, for the rows it showed."""

    path = request.app.state.paths.resource_priority
    form = await request.form()
    current = load_resource_priority_yaml(path)
    names = {row.name for row in priority_rows(current, request.app.state.discover_containers())}

    updated = definition_from_form(
        current, names, {key: str(value) for key, value in form.items()}
    )
    save_resource_priority_yaml(updated, path)

    status = _language(request).t(
        "priority.status.saved",
        priority=len(updated.priority),
        throttled=len(updated.background.containers),
    )

    return RedirectResponse(f"{PREFIX}/?status={quote(status)}", status_code=303)
