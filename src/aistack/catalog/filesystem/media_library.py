from __future__ import annotations

from pathlib import Path
from typing import Any

from aistack.kernel.catalog import Catalog, CatalogItem


class MediaLibraryCatalogBuilder:
    """Build a Catalog from a media library observation.

    One rule: a directory is an item when it holds media, directly or
    below it. No fixed depth is assumed (albums sit at varying levels),
    and non-media folders drop out without a blacklist. The root is not an
    item. Item ids are paths relative to the root; `source` holds the
    absolute path.
    """

    def __init__(self, catalog_id: str, title: str) -> None:
        self.catalog_id = catalog_id
        self.title = title

    def build(self, observation: dict[str, Any]) -> Catalog:
        library = observation["library"]

        root = Path(library["root"])

        return Catalog(
            catalog_id=self.catalog_id,
            title=self.title,
            metadata={
                "source_provider": observation["provider"]["id"],
                "collected_at": observation["collected_at"],
                "root": library["root"],
                "exists": str(library["exists"]),
                "unreadable": str(library["unreadable"]),
                # Files of unknown format: tells a node missing for
                # that reason from one that is empty.
                "unrecognized_extensions": self._census(
                    library["unrecognized_extensions"]
                ),
            },
            items=tuple(
                self._item(entry, root)
                for entry in library["directories"]
                if self._is_node(entry)
            ),
        )

    def _census(self, unrecognized: dict[str, int]) -> str:
        """The unrecognised extensions, most frequent first, as one string
        (`Catalog.metadata` values are strings)."""

        ordered = sorted(
            unrecognized.items(), key=lambda pair: (-pair[1], pair[0])
        )

        return " ".join(
            f"{extension or '(none)'}={count}" for extension, count in ordered
        )

    def _is_node(self, entry: dict[str, Any]) -> bool:
        return bool(entry["relative_path"]) and entry["total_media_files"] > 0

    def _item(self, entry: dict[str, Any], root: Path) -> CatalogItem:
        relative = entry["relative_path"]

        return CatalogItem(
            id=relative,
            label=Path(relative).name,
            kind="directory",
            source=str(root / relative),
            metadata={
                "relative_path": relative,
                "parent": entry["parent"],
                "depth": str(entry["depth"]),
                # Cumulative counts feed capacity; direct counts tell a
                # container from a leaf (a directory can be both).
                "media_files": str(entry["media_files"]),
                "media_bytes": str(entry["media_bytes"]),
                "total_media_files": str(entry["total_media_files"]),
                "total_media_bytes": str(entry["total_media_bytes"]),
            },
        )
