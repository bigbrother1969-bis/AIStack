from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from aistack.network_discovery.definition import NetworkDiscoveryDefinition
from aistack.network_discovery.yaml import (
    load_network_discovery_yaml,
    save_network_discovery_yaml,
)
from aistack.providers.repository import RepositoryProvider

# `claude/PLAN-J11-CONSOLE-2026-09-11.md` §11 — the owner asked,
# mid-session 2026-09-12, for a way to add SSH usernames to
# `network_discovery.yml` without hand-editing it, and specifically
# named "the console" — which already has a precise meaning in this
# heritage (the static, backend-free page decided in §2). Rather
# than turning that static page into one with a backend (reversing
# that decision for the one page it applies to), this is a new,
# separate small screen — the same pattern `priority_ui` and
# `selection_ui` already are — linked from the console as one more
# card, exactly as those two already are.
#
# **LAN-only, on purpose (decided with the owner 2026-09-12).**
# Every candidate SSH username declared here is later tried,
# unattended, against every host a network scan finds live on the
# owner's own LAN (`aistack.cli.network_docker_discover`) — unlike
# `priority_ui`/`selection_ui`, which only ever change what this
# repository *classifies*, a wrong or malicious entry here changes
# what credentials get tried against real machines. No Proxy Host is
# declared for this screen in `console_links.yml`, and none should
# ever be added — it must never become reachable through
# `aistack.persiaut-family.fr`.
REPO_ROOT = Path(__file__).resolve().parents[1]
repository = RepositoryProvider(REPO_ROOT)

DEFINITION_PATH = repository.resolve(
    "src/aistack/network_discovery/definitions/network_discovery.yml"
)

app = FastAPI(title="AIStack Network Discovery UI")
templates = Jinja2Templates(
    directory=str(repository.resolve("network_discovery_ui/templates"))
)


def _page_context(definition: NetworkDiscoveryDefinition) -> dict[str, object]:
    return {
        "cidr": definition.cidr,
        "ssh_key_path_env": definition.ssh_key_path_env,
        "ssh_timeout_seconds": definition.ssh_timeout_seconds,
        "ssh_usernames": definition.ssh_usernames,
    }


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    definition = load_network_discovery_yaml(DEFINITION_PATH)
    context = _page_context(definition)
    context["status"] = request.query_params.get("status")

    return templates.TemplateResponse(
        request=request, name="index.html", context=context
    )


@app.post("/add")
async def add(request: Request):
    """
    Append one candidate SSH username to the declared, ordered list —
    a no-op, not an error, when it is blank or already present, so
    that submitting the form twice (a double click, a retried
    request) never produces a duplicate entry silently tried twice
    against every discovered host.
    """

    form = await request.form()
    username = str(form.get("username", "")).strip()

    definition = load_network_discovery_yaml(DEFINITION_PATH)

    if username and username not in definition.ssh_usernames:
        updated = NetworkDiscoveryDefinition(
            cidr=definition.cidr,
            ssh_key_path_env=definition.ssh_key_path_env,
            ssh_usernames=(*definition.ssh_usernames, username),
            ssh_timeout_seconds=definition.ssh_timeout_seconds,
        )
        save_network_discovery_yaml(updated, DEFINITION_PATH)
        status = f"Ajouté : {username}"
    elif username:
        status = f"Déjà présent : {username}"
    else:
        status = "Nom d'utilisateur vide, rien d'ajouté."

    return RedirectResponse(f"/?status={quote(status)}", status_code=303)


@app.post("/remove")
async def remove(request: Request):
    """
    Remove one declared username — the counterpart to `/add`, kept
    as its own route rather than a single combined "save the whole
    list" form: each action is one explicit, auditable change to a
    file that controls which credentials get tried against real
    machines, not a bulk edit that could silently drop an entry the
    owner meant to keep.
    """

    form = await request.form()
    username = str(form.get("username", "")).strip()

    definition = load_network_discovery_yaml(DEFINITION_PATH)

    if username in definition.ssh_usernames:
        updated = NetworkDiscoveryDefinition(
            cidr=definition.cidr,
            ssh_key_path_env=definition.ssh_key_path_env,
            ssh_usernames=tuple(
                name for name in definition.ssh_usernames if name != username
            ),
            ssh_timeout_seconds=definition.ssh_timeout_seconds,
        )
        save_network_discovery_yaml(updated, DEFINITION_PATH)
        status = f"Retiré : {username}"
    else:
        status = f"Introuvable : {username}"

    return RedirectResponse(f"/?status={quote(status)}", status_code=303)
