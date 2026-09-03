from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from aistack.application.yaml import load_application_definition_yaml
from aistack.catalog.filesystem import MediaLibraryCatalogBuilder
from aistack.generators.filesystem.hardlink import (
    MaterialisationReport,
    materialise_by_hardlink,
)
from aistack.generators.filesystem.yaml import (
    load_last_generation_yaml,
    save_last_generation_yaml,
)
from aistack.kernel.application import ApplicationDefinition
from aistack.kernel.bootstrap import create_kernel
from aistack.providers.filesystem import (
    DEFAULT_MEDIA_EXTENSIONS,
    MediaLibraryProvider,
)
from aistack.providers.repository import RepositoryProvider
from aistack.providers.syncthing.provider import SyncthingProvider
from aistack.selection.capacity import assess_capacity
from aistack.selection.materialisation_status import materialized_nodes
from aistack.selection.subtree import resolve_subtrees
from aistack.selection.workflow import build_view, select_from_view
from aistack.selection.yaml import load_selection_yaml, save_selection_yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
repository = RepositoryProvider(REPO_ROOT)

# **The first Application Definition consumer.** Until step 7 this
# screen read `catalog_file`, a static YAML nobody rewrote when the
# library changed, and `generation_command`, a shell-out to a
# destructive, untested generator. Both are gone: the catalog is
# scanned live from `definition.source_root` on every request
# (decision #8, 2026-08-29), and materialisation calls
# `materialise_by_hardlink` in process. GOV-0002/OS-039's surface
# half, closed.
kernel = create_kernel()

APP_DEF = repository.resolve("selection_ui/definitions/music_android.yml")

app = FastAPI(title="AIStack Selection UI")
templates = Jinja2Templates(
    directory=str(repository.resolve("selection_ui/templates"))
)


def load_app_definition() -> ApplicationDefinition:
    return load_application_definition_yaml(APP_DEF)


def _last_generation_path(definition: ApplicationDefinition) -> Path:
    return repository.resolve(definition.selection_file).with_name(
        f"{definition.app_id}-last-generation.yml"
    )


def _catalog(definition: ApplicationDefinition):
    observation = MediaLibraryProvider(Path(definition.source_root)).collect()

    return MediaLibraryCatalogBuilder(
        catalog_id=definition.catalog_id,
        title=definition.catalog_title,
    ).build(observation)


def _syncthing_status(definition: ApplicationDefinition) -> dict[str, Any] | None:
    """
    `None` when this instance of the family declared no Syncthing
    block at all — a future member of the family might not sync to
    a phone. Never a dict standing in for "not configured", which
    would read on the screen as a daemon that answered.
    """

    if not definition.syncthing:
        return None

    provider = SyncthingProvider(
        url=definition.syncthing.url,
        api_key=os.environ.get(definition.syncthing.api_key_env, ""),
        folder_id=definition.syncthing.folder_id,
        device_id=definition.syncthing.device_id,
        timeout=definition.syncthing.timeout_seconds,
    )

    return provider.collect()["syncthing"]


def _page_context(definition: ApplicationDefinition) -> dict[str, Any]:
    """
    Everything one page load needs, assembled once.

    A dry run of `materialise_by_hardlink` is part of *reading* the
    page — it writes nothing — and it is the single source both the
    per-node materialised/pending status and the "N fichiers à
    créer, M à retirer" summary read from, rather than two separate
    computations that could disagree.
    """

    catalog = _catalog(definition)
    view = build_view(kernel, catalog, definition.view_id)

    selection = load_selection_yaml(
        repository.resolve(definition.selection_file)
    )
    selected = set(selection.selected_ids) if selection else set()

    resolution = resolve_subtrees(catalog, selected)
    capacity = assess_capacity(resolution, definition.capacity_declared_bytes)

    pending = materialise_by_hardlink(
        catalog=catalog,
        resolution=resolution,
        capacity=capacity,
        target_root=Path(definition.target_root),
        media_extensions=DEFAULT_MEDIA_EXTENSIONS,
        dry_run=True,
    )

    materialized = (
        materialized_nodes(pending, resolution)
        if not pending.refused
        else frozenset()
    )

    return {
        "definition": definition,
        "view": view,
        "selected": selected,
        "covered": set(resolution.covered),
        "redundant": set(resolution.redundant),
        "absent": resolution.absent,
        "capacity": capacity,
        "pending": pending,
        "materialized": materialized,
        "syncthing": _syncthing_status(definition),
        "last_generation": load_last_generation_yaml(
            _last_generation_path(definition)
        ),
    }


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    definition = load_app_definition()
    context = _page_context(definition)
    context["status"] = request.query_params.get("status")

    return templates.TemplateResponse(
        request=request, name="index.html", context=context
    )


@app.get("/syncthing-status")
def syncthing_status() -> dict[str, Any] | None:
    """
    The same question `_page_context` asks Syncthing, answered on
    its own so the screen can ask it again every few seconds
    without reloading the whole page — the catalog scan and the
    dry-run materialisation behind the rest of the page cost real
    time on a 2393-node library, and a phone sync over a VPN takes
    minutes: nothing about that justifies redoing the expensive
    half of the page just to learn the completion percentage moved.

    `None` when this instance declares no Syncthing block, exactly
    as `_syncthing_status` already returns it — the screen's own
    JavaScript treats that as "nothing to poll" rather than a
    failure.
    """

    return _syncthing_status(load_app_definition())


@app.post("/save")
def save(selected_ids: list[str] = Form(default=[])):
    definition = load_app_definition()
    catalog = _catalog(definition)
    view = build_view(kernel, catalog, definition.view_id)

    selection = select_from_view(
        view=view,
        selection_id=definition.app_id,
        selected_ids=selected_ids,
        metadata={
            "source_catalog": definition.catalog_id,
            "managed_by": "selection_ui",
        },
    )

    save_selection_yaml(
        selection, repository.resolve(definition.selection_file)
    )

    resolution = resolve_subtrees(catalog, selection.selected_ids)
    capacity = assess_capacity(resolution, definition.capacity_declared_bytes)

    report = materialise_by_hardlink(
        catalog=catalog,
        resolution=resolution,
        capacity=capacity,
        target_root=Path(definition.target_root),
        media_extensions=DEFAULT_MEDIA_EXTENSIONS,
    )

    save_last_generation_yaml(report, _last_generation_path(definition))

    return RedirectResponse(
        f"/?status={_status_message(report, len(selection.selected_ids))}",
        status_code=303,
    )


def _status_message(report: MaterialisationReport, selected_count: int) -> str:
    if report.refused:
        return report.refused

    changed = len(report.linked) + len(report.relinked) + len(report.removed)

    if changed == 0:
        return f"{selected_count} répertoires sélectionnés, déjà à jour."

    return (
        f"{selected_count} répertoires sélectionnés — "
        f"{len(report.linked)} créés, {len(report.relinked)} mis à jour, "
        f"{len(report.removed)} retirés, "
        f"{len(report.pruned)} répertoires vidés."
    )
