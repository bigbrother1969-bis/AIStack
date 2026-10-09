"""
The generalized sync's screen and executor (`ADR-0022`): what a pair
(content, destination) shows, what the screen records, and what the
host executor applies.

**The screen records, the host applies** (§ 6). The web application
writes only the selection, in the data directory
(`sync/selections/<pair>.yml`); the executor, on the host, brings the
pair's folder to it and records what it did (`sync/applied/<pair>.json`).
A hard link between the two read-only and read-write bind mounts of the
web container fails ("Invalid cross-device link", GIGABYTE,
2026-10-09): the music screen's saves had been failing since the Docker
installation.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from aistack.catalog.filesystem import MediaLibraryCatalogBuilder
from aistack.generators.filesystem.hardlink import MaterialisationReport, materialise_by_hardlink
from aistack.kernel.application import ApplicationDefinition, SyncthingDefinition
from aistack.kernel.catalog.core import Catalog
from aistack.kernel.selection.core import Selection
from aistack.providers.filesystem import MediaLibraryProvider
from aistack.selection.capacity import CapacityVerdict
from aistack.selection.materialisation_status import materialized_nodes
from aistack.selection.subtree import SubtreeResolution, resolve_subtrees
from aistack.selection.yaml import load_selection_yaml, save_selection_yaml
from aistack.sync.declaration import (
    SYNCTHING,
    SyncDeclaration,
    excluded,
    extensions,
    folder_for,
    pair_id,
    split_pair,
    target_for,
)

SELECTIONS = Path("sync") / "selections"
APPLIED = Path("sync") / "applied"
# A pair applied less than this long ago, and not changed since, is
# not scanned again: a new album in a ticked directory still arrives
# within the hour.
REFRESH = timedelta(hours=1)


def selection_file(generated: Path, pair: str) -> Path:
    return generated / SELECTIONS / f"{pair}.yml"


def applied_file(generated: Path, pair: str) -> Path:
    return generated / APPLIED / f"{pair}.json"


def read_applied(generated: Path, pair: str) -> dict[str, Any] | None:
    try:
        data = json.loads(applied_file(generated, pair).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def load_selection(generated: Path, pair: str, legacy: Path | None = None) -> Selection | None:
    """The recorded selection; for the music, the old screen's file until
    the first save on this one."""

    path = selection_file(generated, pair)
    if path.exists():
        return load_selection_yaml(path)
    if legacy is not None and legacy.exists():
        return load_selection_yaml(legacy)
    return None


def scan_catalog(declaration: SyncDeclaration, content: str) -> Catalog:
    item = declaration.contents[content]
    observation = MediaLibraryProvider(item.source, media_extensions=extensions(item)).collect()
    catalog = MediaLibraryCatalogBuilder(catalog_id=f"{content}-library", title=item.label("fr")).build(observation)
    if not item.exclude:
        return catalog
    return Catalog(
        catalog_id=catalog.catalog_id,
        title=catalog.title,
        items=tuple(i for i in catalog.items if not excluded(item, i.metadata.get("relative_path", i.id))),
        metadata=catalog.metadata,
    )


def capacity(
    declaration: SyncDeclaration, generated: Path, pair: str, resolution: SubtreeResolution
) -> CapacityVerdict:
    """The destination's quota, less what its other contents took at their last application."""

    content, destination = split_pair(pair)
    quota = declaration.destinations[destination].quota_bytes
    selected = resolution.media_bytes
    if quota <= 0:
        return CapacityVerdict(False, 0, selected, 0, 0.0, True)
    others = 0
    for other in declaration.contents:
        if other == content:
            continue
        record = read_applied(generated, pair_id(other, destination))
        others += int((record or {}).get("selected_bytes") or 0)
    room = max(quota - others, 0)
    return CapacityVerdict(
        declared=True,
        declared_bytes=room,
        selected_bytes=selected,
        remaining_bytes=room - selected,
        percent_used=selected / room * 100 if room else 100.0,
        fits=selected <= room,
    )


def definition(declaration: SyncDeclaration, pair: str, lang: str, device_id: str = "") -> ApplicationDefinition:
    """The pair as the selection screen's own definition, for its template."""

    content, destination = split_pair(pair)
    item, target = declaration.contents[content], declaration.destinations[destination]
    access = declaration.syncthing
    syncthing = (
        SyncthingDefinition(
            url=access.url,
            folder_id=folder_for(declaration, content, destination),
            device_id=device_id or target.device,
            api_key_env=access.api_key_env,
            timeout_seconds=access.timeout_seconds,
        )
        if access is not None and target.kind == SYNCTHING
        else None
    )
    return ApplicationDefinition(
        app_id=pair,
        title=f"{item.label(lang)} → {target.label(lang)}",
        view_id="media-tree",
        source_root=str(item.source),
        target_root=str(target_for(declaration, content, destination)),
        selection_file=str(SELECTIONS / f"{pair}.yml"),
        capacity_declared_bytes=target.quota_bytes,
        syncthing=syncthing,
    )


def _dry_run(declaration: SyncDeclaration, pair: str, catalog: Catalog, resolution: SubtreeResolution, verdict: CapacityVerdict) -> MaterialisationReport:
    content, destination = split_pair(pair)
    return materialise_by_hardlink(
        catalog=catalog,
        resolution=resolution,
        capacity=verdict,
        target_root=target_for(declaration, content, destination),
        media_extensions=extensions(declaration.contents[content]),
        dry_run=True,
    )


def page_context(
    declaration: SyncDeclaration,
    pair: str,
    kernel: Any,
    generated: Path,
    syncthing: Callable[[ApplicationDefinition], "dict[str, Any] | None"],
    lang: str,
    legacy: Path | None = None,
) -> dict[str, Any]:
    from aistack.selection.workflow import build_view

    content, destination = split_pair(pair)
    catalog = scan_catalog(declaration, content)
    view = build_view(kernel, catalog, "media-tree")
    selection = load_selection(generated, pair, legacy)
    selected = set(selection.selected_ids) if selection else set()
    resolution = resolve_subtrees(catalog, selected)
    verdict = capacity(declaration, generated, pair, resolution)
    pending = _dry_run(declaration, pair, catalog, resolution, verdict)
    applied = read_applied(generated, pair)
    the_definition = definition(declaration, pair, lang)
    return {
        "definition": the_definition,
        "view": view,
        "selected": selected,
        "covered": set(resolution.covered),
        "redundant": set(resolution.redundant),
        "absent": resolution.absent,
        "capacity": verdict,
        "pending": pending,
        "materialized": materialized_nodes(pending, resolution) if not pending.refused else frozenset(),
        "syncthing": syncthing(the_definition),
        "last_generation": (
            {"generated_at": applied.get("at", ""), "report": applied} if applied else None
        ),
        "pair": pair,
        "content": declaration.contents[content],
        "destination": declaration.destinations[destination],
        "waiting": waiting(generated, pair),
    }


def record_selection(
    declaration: SyncDeclaration, generated: Path, pair: str, selected_ids: list[str], person: str
) -> Selection:
    """What the screen writes: the selection, who made it, when."""

    content, _ = split_pair(pair)
    known = {item.id for item in scan_catalog(declaration, content).items}
    selection = Selection(
        selection_id=pair,
        catalog_id=f"{content}-library",
        selected_ids=sorted(i for i in set(selected_ids) if i in known),
        metadata={
            "managed_by": "sync",
            "saved_by": person,
            "saved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        },
    )
    save_selection_yaml(selection, selection_file(generated, pair))
    return selection


def waiting(generated: Path, pair: str) -> bool:
    """A selection recorded after the last application."""

    path = selection_file(generated, pair)
    if not path.exists():
        return False
    applied = read_applied(generated, pair)
    if not applied:
        return True
    return path.stat().st_mtime > float(applied.get("selection_mtime") or 0)


def due(generated: Path, pair: str, now: datetime) -> bool:
    if not selection_file(generated, pair).exists():
        # Nothing recorded: the folder is left as it is — never emptied
        # for want of a selection.
        return False
    if waiting(generated, pair):
        return True
    applied = read_applied(generated, pair) or {}
    try:
        last = datetime.fromisoformat(str(applied.get("at")))
    except ValueError:
        return True
    return now - last >= REFRESH


def apply_pair(
    declaration: SyncDeclaration, generated: Path, pair: str, now: datetime | None = None, dry_run: bool = False
) -> dict[str, Any]:
    """Bring the pair's folder to its recorded selection, and say what was done."""

    moment = now or datetime.now(timezone.utc)
    content, destination = split_pair(pair)
    path = selection_file(generated, pair)
    selection = load_selection_yaml(path)
    selected = set(selection.selected_ids) if selection else set()
    catalog = scan_catalog(declaration, content)
    resolution = resolve_subtrees(catalog, selected)
    verdict = capacity(declaration, generated, pair, resolution)
    started = datetime.now(timezone.utc)
    report = materialise_by_hardlink(
        catalog=catalog,
        resolution=resolution,
        capacity=verdict,
        target_root=target_for(declaration, content, destination),
        media_extensions=extensions(declaration.contents[content]),
        dry_run=dry_run,
    )
    record: dict[str, Any] = {
        "at": moment.isoformat(timespec="seconds"),
        "seconds": round((datetime.now(timezone.utc) - started).total_seconds(), 1),
        "selection_mtime": path.stat().st_mtime,
        "selected_bytes": resolution.media_bytes if not report.refused else 0,
        "target": str(target_for(declaration, content, destination)),
        **{key: value for key, value in asdict(report).items()},
    }
    for key in ("linked", "relinked", "removed", "pruned"):
        record[key] = len(record[key])
    record["failed"] = [list(item) for item in record["failed"]][:20]
    if not dry_run:
        target = applied_file(generated, pair)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(".tmp")
        temporary.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        temporary.replace(target)
    return record
