from __future__ import annotations

from aistack.kernel.catalog import Catalog, CatalogItem
from aistack.kernel.catalog.views import CatalogView, CatalogViewItem


class MediaTreeViewEngine:
    """
    Order a media catalog so a human can walk it.

    The catalog is flat and, on the owner's library, 2393 entries
    long — measured 2026-08-29. Flat and alphabetical, that is a
    list in which `Classique/Bach/Cantates` sits between
    `Classique/Bach` and `Classique/Berlioz` by accident of
    spelling and not by belonging. This engine does the one thing
    that turns it into something a person can read: **it orders
    the entries depth-first, every parent immediately before its
    own descendants**, and states each entry's depth.

    A surface can then render an indented, foldable tree from a
    single pass, without knowing the tree. `CatalogView.items` is
    a list, and a list in depth-first order carries a tree
    faithfully — which is why nothing is added to the Kernel's
    view model for this.

    **Siblings are ordered case-insensitively, and deterministic
    with it.** Comparing Python strings compares code points, and
    every capital letter comes before every lowercase one: in the
    owner's library, listed that way, `soum bill` is exiled past
    `Vidéos` to the very end, after two hundred capitalised
    artists. The key is the case-folded label with the raw label
    as tie-breaker, which puts it back among the S's.

    No locale is consulted, and that is a limit accepted rather
    than overlooked: `Bénabar` still sorts after `Blondie`,
    where a French collation would place it beside `Ben Harper`.
    A locale-aware order would be nicer to read and would differ
    between two hosts holding the same library — ENG-TEST-0002 is
    C3 and promises portability across environments, and
    STD-0300 § 6 wants an unchanged input to give an identical
    output. The nicer order is available the day it is declared
    as governed data rather than inherited from an environment
    variable.

    **A node whose parent is absent is attached to the root, not
    dropped.** In a catalog built by `MediaLibraryCatalogBuilder`
    the case cannot arise: a node holds media below it, so every
    ancestor does too, so every ancestor is a node. The engine
    does not rely on that. A view that silently omitted what it
    could not place would hide exactly the defect worth seeing,
    and this heritage has paid for that shape more than once.
    """

    view_id = "media-tree"

    def build(self, catalog: Catalog) -> CatalogView:
        present = {item.id for item in catalog.items}

        children: dict[str, list[CatalogItem]] = {}

        for item in catalog.items:
            parent = item.metadata.get("parent", "")

            if parent not in present:
                parent = ""

            children.setdefault(parent, []).append(item)

        for siblings in children.values():
            siblings.sort(key=lambda item: (item.label.casefold(), item.label))

        ordered: list[CatalogViewItem] = []

        self._walk("", children, ordered)

        return CatalogView(
            view_id=self.view_id,
            source_catalog_id=catalog.catalog_id,
            title=f"{catalog.title} Tree View",
            items=ordered,
            metadata={
                "purpose": "selection",
                "domain": "media",
                # What the surface would otherwise recompute, and
                # what it must be able to show: where this was
                # read, and what the reading left out. The UI runs
                # on a host nobody reviewing this code observes.
                "root": catalog.metadata.get("root", ""),
                "exists": catalog.metadata.get("exists", ""),
                "unrecognized_extensions": catalog.metadata.get(
                    "unrecognized_extensions", ""
                ),
                "node_count": str(len(ordered)),
            },
        )

    def _walk(
        self,
        parent: str,
        children: dict[str, list[CatalogItem]],
        ordered: list[CatalogViewItem],
    ) -> None:
        """
        Depth-first, iteratively.

        The owner's tree is five levels deep today and recursion
        would carry it comfortably. It is written as a stack
        because the depth of a directory tree is an input, not a
        property of this code, and a view that raises on a deep
        library would fail in the surface with nothing to read.
        """

        stack = list(reversed(children.get(parent, [])))

        while stack:
            item = stack.pop()

            ordered.append(self._item(item, children))

            stack.extend(reversed(children.get(item.id, [])))

    def _item(
        self, item: CatalogItem, children: dict[str, list[CatalogItem]]
    ) -> CatalogViewItem:
        return CatalogViewItem(
            id=item.id,
            label=item.label,
            metadata={
                **item.metadata,
                "source": item.source,
                # So the surface can draw a fold control without
                # looking ahead in the list.
                "has_children": str(bool(children.get(item.id))),
            },
        )
