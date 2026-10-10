from __future__ import annotations

from aistack.kernel.catalog import Catalog, CatalogItem
from aistack.kernel.catalog.views import CatalogView, CatalogViewItem


class MediaTreeViewEngine:
    """Order a flat media catalog depth-first, each parent immediately
    before its descendants, so a surface can render a foldable tree in one
    pass.

    Siblings sort by case-folded label, then raw label. No locale is used,
    so the order is identical on every host (`Bénabar` sorts after
    `Blondie`). A node whose parent is absent is attached to the root
    rather than dropped.
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
                # Where the library was read and what was left out,
                # for the surface to show.
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
        """Depth-first walk with an explicit stack, so a deep tree cannot hit
        the recursion limit."""

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
                # Lets the surface draw a fold control without look-ahead.
                "has_children": str(bool(children.get(item.id))),
            },
        )
