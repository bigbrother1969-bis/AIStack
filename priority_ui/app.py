from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from aistack.priority.definition import (
    BackgroundPriorityDefinition,
    ContainerPriorityDefinition,
    CpuThresholdDetectorDefinition,
    JellyfinDetectorDefinition,
    PriorityAppDefinition,
    ResourcePriorityDefinition,
)
from aistack.priority.discovery import DiscoveredContainer, resolve_discovered_containers
from aistack.priority.yaml import (
    load_resource_priority_yaml,
    save_resource_priority_yaml,
)
from aistack.providers.docker import DockerProvider
from aistack.providers.repository import RepositoryProvider


REPO_ROOT = Path(__file__).resolve().parents[1]
repository = RepositoryProvider(REPO_ROOT)

# Decision 2 of claude/PLAN-DYNAMIC-CONTAINER-PRIORITY-2026-09-03.md
# — "nouvel écran web": the same file the étape 4 monitor
# (`aistack.cli.resource_priority_monitor`) reads, edited here rather
# than by hand.
DEFINITION_PATH = repository.resolve(
    "src/aistack/priority/definitions/resource_priority.yml"
)

app = FastAPI(title="AIStack Priority UI")
templates = Jinja2Templates(
    directory=str(repository.resolve("priority_ui/templates"))
)


def _discovered() -> tuple[DiscoveredContainer, ...]:
    """
    What Docker reports right now — decision 1's own generic
    replacement for the hardcoded fourteen-container list. No new
    provider: `DockerProvider` already observes `docker ps -a`;
    `resolve_discovered_containers` shapes it for this screen.

    **A Docker daemon this screen cannot reach reads as "nothing
    discovered", not a 500 page.** Unlike `JellyfinProvider`/
    `SyncthingProvider`, `DockerProvider` predates this project's
    "unreachable is a state, not an exception" convention and still
    raises (`subprocess.run(..., check=True)`) when the daemon is
    down. Changing that provider's own contract is out of scope
    here — other, older consumers may depend on it raising — so this
    is the one call site absorbing it: the owner should still be
    able to load the screen and see the governed YAML's existing
    classification even on a day Docker itself is unreachable, the
    same reasoning `is_playing_now`'s own decision #4 already
    applied to a different unreachable dependency.
    """

    try:
        return resolve_discovered_containers(DockerProvider().collect())
    except subprocess.CalledProcessError:
        return ()


def _rows(definition: ResourcePriorityDefinition) -> list[dict[str, Any]]:
    """
    Every discovered container, alongside whatever the governed
    definition currently says about it — the join `priority_ui`'s
    own screen exists to let the owner edit, one row at a time.

    **A container the governed YAML names but Docker does not
    currently report is still shown.** A priority app or a
    background container that is temporarily stopped, or whose name
    was typed by hand and no longer matches anything running, is
    not silently dropped from the screen — the owner should see it
    and decide, not lose track of it because `docker ps -a` did not
    list it this second.
    """

    priority_by_name = {app.container: app for app in definition.priority}
    background_by_name = {c.name: c for c in definition.background.containers}

    discovered_by_name = {c.name: c for c in _discovered()}
    every_name = sorted(
        set(discovered_by_name) | set(priority_by_name) | set(background_by_name)
    )

    rows = []

    for name in every_name:
        container = discovered_by_name.get(name)
        priority_app = priority_by_name.get(name)
        background_container = background_by_name.get(name)

        if priority_app is not None:
            classification = "priority"
        elif background_container is not None:
            classification = "throttled"
        else:
            classification = "ignored"

        rows.append(
            {
                "name": name,
                "image": container.image if container else "",
                "running": container.running if container else None,
                "status": container.status if container else "",
                "classification": classification,
                "priority_app": priority_app,
                "background_container": background_container,
            }
        )

    return rows


def _page_context() -> dict[str, Any]:
    definition = load_resource_priority_yaml(DEFINITION_PATH)

    return {
        "rows": _rows(definition),
        "unlimited_cpus": definition.unlimited_cpus,
        "grace_seconds": definition.grace_seconds,
        "default_throttled_cpus": definition.background.default_throttled_cpus,
    }


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    context = _page_context()
    context["status"] = request.query_params.get("status")

    return templates.TemplateResponse(
        request=request, name="index.html", context=context
    )


@app.post("/save")
async def save(request: Request):
    """
    Rewrite the governed definition from this screen's own form.

    **One classification per discovered name, read from the form
    rather than declared as fixed `Form(...)` parameters** — the
    set of containers is whatever Docker reports this load, not a
    fixed schema `priority_ui/app.py` could name in advance. Field
    names are namespaced by container (`classification__<name>`,
    `normal_cpus__<name>`, ...), the same shape the template's own
    `name="..."` attributes write.

    **Ignored is every name absent from both output lists** —
    decision 3: nothing here is a "delete" action distinct from
    simply not classifying a container as priority or throttled.
    """

    form = await request.form()
    current = load_resource_priority_yaml(DEFINITION_PATH)

    priority_entries: list[PriorityAppDefinition] = []
    background_entries: list[ContainerPriorityDefinition] = []

    for name in {row["name"] for row in _rows(current)}:
        classification = form.get(f"classification__{name}", "ignored")

        if classification == "priority":
            priority_entries.append(_priority_app_from_form(form, name))
        elif classification == "throttled":
            background_entries.append(_background_container_from_form(form, name))

    updated = ResourcePriorityDefinition(
        priority=tuple(
            sorted(priority_entries, key=lambda app: app.container)
        ),
        background=BackgroundPriorityDefinition(
            default_throttled_cpus=current.background.default_throttled_cpus,
            containers=tuple(
                sorted(background_entries, key=lambda c: c.name)
            ),
        ),
        unlimited_cpus=current.unlimited_cpus,
        grace_seconds=current.grace_seconds,
    )

    save_resource_priority_yaml(updated, DEFINITION_PATH)

    return RedirectResponse(
        f"/?status={len(priority_entries)} appli(s) prioritaire(s), "
        f"{len(background_entries)} conteneur(s) au ralenti.",
        status_code=303,
    )


def _priority_app_from_form(form: Any, name: str) -> PriorityAppDefinition:
    detector_type = form.get(f"detector_type__{name}", "jellyfin")

    if detector_type == "cpu_threshold":
        detector = CpuThresholdDetectorDefinition(
            threshold_percent=_form_float(
                form, f"cpu_threshold_percent__{name}", default=50.0
            ),
            sustained_seconds=_form_float(
                form, f"cpu_sustained_seconds__{name}", default=15.0
            ),
        )
    else:
        detector = JellyfinDetectorDefinition(
            url=str(form.get(f"jellyfin_url__{name}", "")),
            api_key_env=str(form.get(f"jellyfin_api_key_env__{name}", "")),
            timeout_seconds=_form_float(
                form, f"jellyfin_timeout__{name}", default=5.0
            ),
        )

    return PriorityAppDefinition(
        container=name,
        normal_cpus=_form_float(form, f"normal_cpus__{name}", default=0.0),
        boosted_cpus=_form_float(form, f"boosted_cpus__{name}", default=0.0),
        detector=detector,
    )


def _background_container_from_form(
    form: Any, name: str
) -> ContainerPriorityDefinition:
    raw = str(form.get(f"throttled_normal_cpus__{name}", "")).strip()

    return ContainerPriorityDefinition(
        name=name, normal_cpus=float(raw) if raw else None
    )


def _form_float(form: Any, field: str, default: float) -> float:
    raw = str(form.get(field, "")).strip()

    try:
        return float(raw) if raw else default
    except ValueError:
        return default
