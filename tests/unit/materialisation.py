"""Materialise a selection the way the Kernel does, for a test that needs the result on disk."""

from __future__ import annotations

from pathlib import Path

from aistack.generators.filesystem.hardlink import (
    SYNC_ARTEFACTS,
    MaterialisationReport,
    preview_materialisation,
)
from aistack.kernel.catalog import Catalog
from aistack.selection.capacity import CapacityVerdict
from aistack.selection.subtree import SubtreeResolution
from aistack.transaction.contracts.selection_materialise import SelectionMaterialise
from aistack.transaction.engines.selection_materialise import SelectionMaterialiseEngine


def materialise_by_hardlink(
    catalog: Catalog,
    resolution: SubtreeResolution,
    capacity: CapacityVerdict,
    target_root: Path,
    media_extensions: frozenset[str],
    preserve_names: frozenset[str] = SYNC_ARTEFACTS,
    dry_run: bool = False,
) -> MaterialisationReport:
    if dry_run:
        return preview_materialisation(
            catalog, resolution, capacity, target_root, media_extensions, preserve_names
        )

    report = SelectionMaterialiseEngine().execute(
        SelectionMaterialise(catalog, resolution, capacity, target_root, media_extensions, preserve_names)
    )
    assert isinstance(report, MaterialisationReport)

    return report
