from __future__ import annotations

from pathlib import Path
from typing import Any

from aistack.kernel.catalog import Catalog, CatalogItem


class MediaLibraryCatalogBuilder:
    """
    Build a governed Catalog from a media library observation.

    **This is where the interpretation happens**, and it is one
    rule: *a node belongs to the catalog when it holds media,
    directly or below it*. The provider reports every directory
    without deciding; this decides.

    The rule was chosen over a fixed depth because the owner's
    tree refuses one. Measured 2026-08-29: five levels, 1949
    directories holding audio directly — 34 at the first level,
    1386 at the second, 381 at the third, 130 at the fourth, 18 at
    the fifth. `Classique` stacks composer then album; box sets
    add a disc below the album; seventeen artists keep loose
    tracks beside their albums. "Album" is a convention that tree
    honours on average and not in particular, so the catalog names
    no level: it names the nodes, and the human ticks the one they
    mean. Decided 2026-08-29 by the owner.

    The same rule is what keeps `lost+found`, a Steam library and
    a folder of cover scans out, **without naming any of them**.
    A blacklist would have had to be maintained against a tree
    that changes; this excludes them for the reason they do not
    belong — there is no music under them — and admits them the
    day there is.

    **The root itself is not an item.** It is the subject of the
    catalog, not an entry in it, and a tick on it would mean
    "everything" — a selection that has no capacity to fit in.

    **Identifiers are paths relative to the root**, so they
    survive a library that moves and stay readable to the human
    who ticked them. `source` carries the absolute path, which is
    deployment knowledge and changes with the host — the same
    split the Docker catalog makes between what a thing is called
    and where it currently lives.
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
                # What the observation held and this catalog does
                # not: the files no rule could place. A node
                # missing because its format is unknown looks
                # exactly like a node missing because it is empty,
                # and this is the difference, carried to the
                # surface that displays the catalog.
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
        """
        The unrecognised extensions, heaviest first, as one line.

        `Catalog.metadata` is `dict[str, str]`; a census that has
        to survive that is a census that gets read.
        """

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
                # Both counts travel. The cumulative one is what a
                # capacity bar adds up; the direct one is what
                # tells a container from a leaf, and seventeen
                # directories in this library are both at once.
                "media_files": str(entry["media_files"]),
                "media_bytes": str(entry["media_bytes"]),
                "total_media_files": str(entry["total_media_files"]),
                "total_media_bytes": str(entry["total_media_bytes"]),
            },
        )
