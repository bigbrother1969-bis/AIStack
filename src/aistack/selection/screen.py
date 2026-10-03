"""
What the *Selection UI* screen reads, shows and does (`ADR-0012` § 4).

Computed in `selection_ui/app.py` at the repository root until
2026-10-03, outside the governed suite; the route in
`aistack.web.selection` now only reads the request and calls these.

**The first Application Definition consumer.** The catalog is scanned
live from `definition.source_root` on every request (decision #8,
2026-08-29) and materialisation calls `materialise_by_hardlink` in
process (`GOV-0002/OS-039`). The two host-touching reads that are not
the library itself — Syncthing, and where the repository keeps the
selection file — reach these functions as arguments.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from aistack.catalog.filesystem import MediaLibraryCatalogBuilder
from aistack.generators.filesystem.hardlink import (
    MaterialisationReport,
    materialise_by_hardlink,
)
from aistack.generators.filesystem.yaml import load_last_generation_yaml, save_last_generation_yaml
from aistack.i18n import Translator
from aistack.kernel.application import ApplicationDefinition
from aistack.providers.filesystem import DEFAULT_MEDIA_EXTENSIONS, MediaLibraryProvider
from aistack.providers.syncthing.provider import SyncthingProvider
from aistack.selection.capacity import assess_capacity
from aistack.selection.materialisation_status import materialized_nodes
from aistack.selection.subtree import resolve_subtrees
from aistack.selection.workflow import build_view, select_from_view
from aistack.selection.yaml import load_selection_yaml, save_selection_yaml

SyncthingStatus = Callable[[ApplicationDefinition], "dict[str, Any] | None"]


def read_syncthing(definition: ApplicationDefinition) -> dict[str, Any] | None:
    """
    What Syncthing reports for this instance's folder and device.

    `None` when this instance of the family declared no Syncthing block
    at all — never a dict standing in for "not configured", which would
    read on the screen as a daemon that answered.
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

    result: dict[str, Any] = provider.collect()["syncthing"]

    return result


def selection_path(definition: ApplicationDefinition, repository_root: Path) -> Path:
    return repository_root / definition.selection_file


def last_generation_path(definition: ApplicationDefinition, repository_root: Path) -> Path:
    return selection_path(definition, repository_root).with_name(
        f"{definition.app_id}-last-generation.yml"
    )


def scan_catalog(definition: ApplicationDefinition) -> Any:
    observation = MediaLibraryProvider(Path(definition.source_root)).collect()

    return MediaLibraryCatalogBuilder(
        catalog_id=definition.catalog_id,
        title=definition.catalog_title,
    ).build(observation)


def page_context(
    definition: ApplicationDefinition,
    kernel: Any,
    repository_root: Path,
    syncthing: SyncthingStatus,
) -> dict[str, Any]:
    """
    Everything one page load needs, assembled once.

    A dry run of `materialise_by_hardlink` is part of *reading* the
    page — it writes nothing — and is the single source both the
    per-node materialised/pending status and the "N files to create, M
    to remove" summary read from, rather than two computations that
    could disagree.
    """

    catalog = scan_catalog(definition)
    view = build_view(kernel, catalog, definition.view_id)

    selection = load_selection_yaml(selection_path(definition, repository_root))
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
        materialized_nodes(pending, resolution) if not pending.refused else frozenset()
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
        "syncthing": syncthing(definition),
        "last_generation": load_last_generation_yaml(
            last_generation_path(definition, repository_root)
        ),
    }


def save_and_materialise(
    definition: ApplicationDefinition,
    kernel: Any,
    repository_root: Path,
    selected_ids: list[str],
) -> tuple[MaterialisationReport, int]:
    """
    Record the selection the screen submitted, then materialise it for
    real — the report and how many items the selection holds.
    """

    catalog = scan_catalog(definition)
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

    save_selection_yaml(selection, selection_path(definition, repository_root))

    resolution = resolve_subtrees(catalog, selection.selected_ids)
    capacity = assess_capacity(resolution, definition.capacity_declared_bytes)

    report = materialise_by_hardlink(
        catalog=catalog,
        resolution=resolution,
        capacity=capacity,
        target_root=Path(definition.target_root),
        media_extensions=DEFAULT_MEDIA_EXTENSIONS,
    )

    save_last_generation_yaml(report, last_generation_path(definition, repository_root))

    return report, len(selection.selected_ids)


def status_message(report: MaterialisationReport, selected_count: int, t: Translator) -> str:
    """What the screen says after a save — the refusal itself when there was one."""

    if report.refused:
        return report.refused

    changed = len(report.linked) + len(report.relinked) + len(report.removed)

    if changed == 0:
        return t("selection.status.up_to_date", count=selected_count)

    return t(
        "selection.status.changed",
        count=selected_count,
        linked=len(report.linked),
        relinked=len(report.relinked),
        removed=len(report.removed),
        pruned=len(report.pruned),
    )
