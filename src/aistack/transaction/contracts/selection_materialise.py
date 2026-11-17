"""Knowledge Transaction - the payload of a `selection.materialise` operation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from aistack.generators.filesystem.hardlink import SYNC_ARTEFACTS
from aistack.kernel.catalog import Catalog
from aistack.selection.capacity import CapacityVerdict
from aistack.selection.subtree import SubtreeResolution

KIND = "selection.materialise"


@dataclass(frozen=True, slots=True)
class SelectionMaterialise:
    """
    A selection to bring to a device's folder, with hard links: the
    catalog it was made on, what it resolves to, the capacity verdict, the
    folder and the media extensions. `preserve_names` are left alone at any
    depth (Syncthing's own files).
    """

    catalog: Catalog
    resolution: SubtreeResolution
    capacity: CapacityVerdict
    target_root: Path
    media_extensions: frozenset[str]
    preserve_names: frozenset[str] = SYNC_ARTEFACTS
