"""
*Découverte réseau* — the candidate SSH usernames a LAN scan tries
(`ADR-0012`; the screen `network_discovery_ui` served on port 8184
until 2026-10-03).

**LAN-only, on purpose (decided with the owner 2026-09-12).** Every
name declared here is later tried, unattended, against every live host
`aistack.cli.network_docker_discover` finds on the owner's LAN: a wrong
or malicious entry changes what credentials are tried against real
machines. The whole router is `LAN_ONLY`; it must never answer through
`aistack.persiaut-family.fr`.

A thin adapter: the change itself is `aistack.network_discovery
.usernames`, tested on its own; this router reads the form, writes the
definition only when something changed, and redirects with the
localized outcome.
"""

from __future__ import annotations

from collections.abc import Callable
from urllib.parse import quote

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from aistack.i18n import LANGUAGE_COOKIE, LANGUAGE_PARAMETER
from aistack.i18n.web import PageLanguage, page_language
from aistack.network_discovery.definition import NetworkDiscoveryDefinition
from aistack.network_discovery.usernames import (
    UsernameChange,
    UsernameOutcome,
    add_username,
    remove_username,
)
from aistack.network_discovery.yaml import (
    load_network_discovery_yaml,
    save_network_discovery_yaml,
)
from aistack.web.authentication import ADMIN_ACTION, SIGNED_IN_ONLY
from aistack.web.exposure import LAN_ONLY
from aistack.web.templating import templates

PREFIX = "/network-discovery"

router = APIRouter(dependencies=[LAN_ONLY, SIGNED_IN_ONLY])

# Spelled out, not built from the enum's value, so the suite's catalog
# check finds every key this screen asks for.
STATUS_KEYS: dict[UsernameChange, str] = {
    UsernameChange.ADDED: "network_discovery.status.added",
    UsernameChange.ALREADY: "network_discovery.status.already",
    UsernameChange.EMPTY: "network_discovery.status.empty",
    UsernameChange.REMOVED: "network_discovery.status.removed",
    UsernameChange.NOT_FOUND: "network_discovery.status.not_found",
}

Change = Callable[[NetworkDiscoveryDefinition, str], UsernameOutcome]


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
    definition = load_network_discovery_yaml(request.app.state.paths.network_discovery)

    context: dict[str, object] = {
        "base": PREFIX,
        "cidr": definition.cidr,
        "ssh_key_path_env": definition.ssh_key_path_env,
        "ssh_timeout_seconds": definition.ssh_timeout_seconds,
        "ssh_usernames": definition.ssh_usernames,
        "status": request.query_params.get("status"),
        **language.context(),
    }

    response = templates.TemplateResponse(
        request=request, name="network_discovery/index.html", context=context
    )

    if language.cookie is not None:
        response.headers.append("set-cookie", language.cookie)

    return response


async def _apply(request: Request, change: Change) -> RedirectResponse:
    t = _language(request).t
    form = await request.form()
    path = request.app.state.paths.network_discovery

    outcome = change(load_network_discovery_yaml(path), str(form.get("username", "")))

    if outcome.changed:
        save_network_discovery_yaml(outcome.definition, path)

    status = t(STATUS_KEYS[outcome.change], username=outcome.username)

    return RedirectResponse(f"{PREFIX}/?status={quote(status)}", status_code=303)


@router.post("/add", include_in_schema=False, dependencies=[ADMIN_ACTION])
async def add(request: Request) -> RedirectResponse:
    return await _apply(request, add_username)


@router.post("/remove", include_in_schema=False, dependencies=[ADMIN_ACTION])
async def remove(request: Request) -> RedirectResponse:
    return await _apply(request, remove_username)
