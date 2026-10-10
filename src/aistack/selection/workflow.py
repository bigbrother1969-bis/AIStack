from __future__ import annotations

from aistack.kernel import Kernel
from aistack.kernel.catalog import Catalog
from aistack.kernel.catalog.views import CatalogView
from aistack.kernel.selection import Selection
from aistack.kernel.selection.engine import SelectionEngine
from aistack.kernel.selection.strategies import ByIdsSelectionStrategy


def build_view(kernel: Kernel, catalog: Catalog, view_id: str) -> CatalogView:
    """Build the Catalog View a surface displays.

    The engine is looked up by `view_id`, so which view a surface shows is
    data, not a class named in code (`ADR-0002`).
    """

    engine = kernel.registries.catalog_views.get(view_id)

    return engine.build(catalog)


def select_from_view(
    view: CatalogView,
    selection_id: str,
    selected_ids: list[str],
    metadata: dict[str, str] | None = None,
) -> Selection:
    """Build a Selection from a Catalog View and explicit identifiers.

    Kept outside `selection_ui` so the workflow is testable without a web
    framework. The strategy is constructed here, not taken from a registry,
    because `ByIdsSelectionStrategy` carries per-request identifiers; the
    engine delegates the criterion to it (`ADR-0003`).
    """

    engine = SelectionEngine()

    return engine.select(
        view=view,
        selection_id=selection_id,
        strategy=ByIdsSelectionStrategy(selected_ids),
        metadata=metadata,
    )
