"""What the Selection UI screen reads, shows and does (`ADR-0012` § 4).

The route in `aistack.web.selection` only parses the request and calls
these. The catalog is scanned live from `definition.source_root` on each
request; the materialisation itself is the Kernel's `selection.materialise`.
Syncthing status and the repository root are passed in as arguments.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from aistack.catalog.filesystem import MediaLibraryCatalogBuilder
from aistack.generators.filesystem.hardlink import (
    MaterialisationReport,
    preview_materialisation,
)
from aistack.generators.filesystem.yaml import load_last_generation_yaml
from aistack.i18n import Translator
from aistack.application import ApplicationDefinition
from aistack.providers.filesystem import DEFAULT_MEDIA_EXTENSIONS, MediaLibraryProvider
from aistack.providers.syncthing.provider import SyncthingProvider
from aistack.selection.capacity import assess_capacity
from aistack.selection.materialisation_status import materialized_nodes
from aistack.selection.subtree import resolve_subtrees
from aistack.selection.workflow import build_view
from aistack.selection.yaml import load_selection_yaml

SyncthingStatus = Callable[[ApplicationDefinition], "dict[str, Any] | None"]


def read_syncthing(definition: ApplicationDefinition) -> dict[str, Any] | None:
    """What Syncthing reports for this instance's folder and device.

    `None` when no Syncthing block is declared, so "not configured" is
    never shown as a daemon that answered.
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
    """Everything one page load needs.

    A preview of the materialisation (`preview_materialisation`, writes nothing) feeds both the
    per-node status and the "N to create, M to remove" summary, so they
    cannot disagree.
    """

    catalog = scan_catalog(definition)
    view = build_view(kernel, catalog, definition.view_id)

    selection = load_selection_yaml(selection_path(definition, repository_root))
    selected = set(selection.selected_ids) if selection else set()

    resolution = resolve_subtrees(catalog, selected)
    capacity = assess_capacity(resolution, definition.capacity_declared_bytes)

    pending = preview_materialisation(
        catalog=catalog,
        resolution=resolution,
        capacity=capacity,
        target_root=Path(definition.target_root),
        media_extensions=DEFAULT_MEDIA_EXTENSIONS,
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
