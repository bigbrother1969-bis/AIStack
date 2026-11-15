"""*Nouveautés*: the containers and machines that appeared and that nothing declares. LAN only.

Reads what the vigil noted (`arrivals-state.json`), hides what a
declaration now covers or the owner set aside, and offers three clicks:
declare a container (written into `service_categorization.yml`, a dated
copy kept), set it aside, or note a machine as known. A machine is never
added by a click: it needs a collector installed on it first, so the
screen only shows the lines to add (ADR-0026).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from aistack.architecture.yaml import load_service_categorization_yaml
from aistack.arrivals import state as store
from aistack.arrivals.declare import Outcome, declare_container
from aistack.arrivals.load import load_arrivals_yaml
from aistack.arrivals.propose import host_block, suggested_description, suggested_name
from aistack.hosts.records import load_hosts_declaration
from aistack.i18n import LANGUAGE_COOKIE, LANGUAGE_PARAMETER
from aistack.i18n.web import PageLanguage, page_language
from aistack.web.authentication import ADMIN_ACTION, SIGNED_IN_ONLY
from aistack.web.exposure import LAN_ONLY
from aistack.web.templating import templates

PREFIX = "/arrivals"
NEW_CATEGORY = "__new__"

router = APIRouter(dependencies=[LAN_ONLY, SIGNED_IN_ONLY])

# Spelled out, not built from the enum value, so the catalog test finds every key.
STATUS_KEYS: dict[Outcome, str] = {
    Outcome.DECLARED: "arrivals.status.declared",
    Outcome.ALREADY: "arrivals.status.already",
    Outcome.NO_CATEGORY: "arrivals.status.no_category",
    Outcome.UNSUPPORTED: "arrivals.status.unsupported",
    Outcome.INVALID: "arrivals.status.invalid",
}


def _language(request: Request) -> PageLanguage:
    return page_language(
        request.query_params.get(LANGUAGE_PARAMETER),
        request.cookies.get(LANGUAGE_COOKIE),
        request.app.state.languages,
    )


def _declared(path: Path) -> tuple[set[str], list[str]]:
    """The containers a service declares, and the categories, in the file's order."""

    try:
        categorization = load_service_categorization_yaml(path)
    except (OSError, ValueError):
        return set(), []

    containers = {s.container for c in categorization.categories for s in c.services if s.container}

    return containers, [c.name for c in categorization.categories]


def _traced_addresses(generated: Path) -> set[str]:
    try:
        return {host.address for host in load_hosts_declaration(generated).hosts if host.address}
    except (OSError, ValueError):
        return set()


@router.get("", response_class=HTMLResponse, include_in_schema=False)
@router.get("/", response_class=HTMLResponse, include_in_schema=False)
def index(request: Request) -> Response:
    language = _language(request)
    generated: Path = request.app.state.generated_dir
    paths = request.app.state.paths
    definition = load_arrivals_yaml(paths.arrivals)
    state = store.read_state(generated)
    decisions = store.read_decisions(generated)
    declared, categories = _declared(paths.categorization)

    ignored = set(decisions["ignored_containers"]) | set(definition.ignore)
    containers = [
        {
            "name": name,
            "where": entry.get("host"),
            "image": entry.get("image"),
            "ports": entry.get("ports"),
            "gpu": bool(entry.get("gpu")),
            "since": str(entry.get("since", "")).replace("T", " "),
            "suggested_name": suggested_name(name),
            "suggested_description": suggested_description(entry.get("image"), entry.get("ports"), bool(entry.get("gpu"))),
        }
        for name, entry in sorted((state.get("containers") or {}).items())
        if entry.get("announced") and name not in declared and name not in ignored
    ]

    known = set(decisions["known_hosts"]) | set(definition.known_hosts) | _traced_addresses(generated)
    hosts = [
        {
            "address": address,
            "user": entry.get("user"),
            "containers": entry.get("containers"),
            "since": str(entry.get("since", "")).replace("T", " "),
            "block": host_block(address, entry.get("user")),
        }
        for address, entry in sorted((state.get("hosts") or {}).items())
        if address not in known
    ]

    context: dict[str, object] = {
        "base": PREFIX,
        "definition": definition,
        "state": state,
        "containers": containers,
        "hosts": hosts,
        "categories": categories,
        "new_category": NEW_CATEGORY,
        "ignored_containers": decisions["ignored_containers"],
        "ignored_hosts": decisions["known_hosts"],
        "status": request.query_params.get("status"),
        **language.context(),
    }

    response = templates.TemplateResponse(request=request, name="arrivals/index.html", context=context)

    if language.cookie is not None:
        response.headers.append("set-cookie", language.cookie)

    return response


def _back(message: str) -> RedirectResponse:
    return RedirectResponse(f"{PREFIX}/?status={quote(message)}", status_code=303)


@router.post("/declare", include_in_schema=False, dependencies=[ADMIN_ACTION])
async def declare(request: Request) -> RedirectResponse:
    t = _language(request).t
    form = await request.form()
    chosen = str(form.get("category", ""))
    new = chosen == NEW_CATEGORY
    container = str(form.get("container", ""))
    category = str(form.get("new_category", "")) if new else chosen

    outcome = declare_container(
        request.app.state.paths.categorization,
        name=str(form.get("name", "")),
        container=container,
        description=str(form.get("description", "")),
        category=category,
        new_category=new,
        now=datetime.now(),
    )

    return _back(t(STATUS_KEYS[outcome], name=str(form.get("name", "")).strip() or container, category=category.strip()))


def _decide(request: Request, key: str, name: str, add: bool) -> None:
    directory: Path = request.app.state.generated_dir
    decisions = store.read_decisions(directory)
    items = set(decisions[key])
    items.add(name) if add else items.discard(name)
    decisions[key] = sorted(items)
    store.write_decisions(directory, decisions)


@router.post("/ignore", include_in_schema=False, dependencies=[ADMIN_ACTION])
async def ignore(request: Request) -> RedirectResponse:
    t = _language(request).t
    name = str((await request.form()).get("container", "")).strip()

    if name:
        _decide(request, "ignored_containers", name, add=True)

    return _back(t("arrivals.status.ignored", name=name))


@router.post("/known", include_in_schema=False, dependencies=[ADMIN_ACTION])
async def known(request: Request) -> RedirectResponse:
    t = _language(request).t
    address = str((await request.form()).get("address", "")).strip()

    if address:
        _decide(request, "known_hosts", address, add=True)

    return _back(t("arrivals.status.known", name=address))


@router.post("/restore", include_in_schema=False, dependencies=[ADMIN_ACTION])
async def restore(request: Request) -> RedirectResponse:
    t = _language(request).t
    form = await request.form()
    name = str(form.get("name", "")).strip()
    key = "known_hosts" if form.get("kind") == "host" else "ignored_containers"

    if name:
        _decide(request, key, name, add=False)

    return _back(t("arrivals.status.restored", name=name))
