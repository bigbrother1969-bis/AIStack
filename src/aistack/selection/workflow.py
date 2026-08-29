from __future__ import annotations

from aistack.kernel import Kernel
from aistack.kernel.catalog import Catalog
from aistack.kernel.catalog.views import CatalogView
from aistack.kernel.selection import Selection
from aistack.kernel.selection.engine import SelectionEngine
from aistack.kernel.selection.strategies import ByIdsSelectionStrategy


def build_view(kernel: Kernel, catalog: Catalog, view_id: str) -> CatalogView:
    """
    Produce the Catalog View a surface displays.

    **The engine is retrieved by identifier**, so which view a
    surface shows is governed data rather than a class named in
    application code. ADR-0002 § *Decision*.
    """

    engine = kernel.registries.catalog_views.get(view_id)

    return engine.build(catalog)


def select_from_view(
    view: CatalogView,
    selection_id: str,
    selected_ids: list[str],
    metadata: dict[str, str] | None = None,
) -> Selection:
    """
    Produce a Selection from a Catalog View and explicit identifiers.

    **This function exists so that the chain can be tested
    without a web framework.** `selection_ui` is a top-level
    package whose dependencies — `fastapi`, `starlette`,
    `jinja2` — this project does not declare: `pyproject.toml`
    declares `PyYAML` and nothing else. Testing the HTTP layer
    would mean adding dependencies to the heritage, which
    ADR-0001 governs. Extracting the logic costs nothing and
    leaves the handlers two lines each.

    *It is also where the logic belonged. A selection workflow in
    an HTTP handler is the shape this heritage keeps removing:
    knowledge embedded in the surface that happens to invoke it.*

    **The strategy is constructed here rather than retrieved.**
    `ByIdsSelectionStrategy` carries its identifiers in its
    constructor, so a strategy configured per request is not a
    registry entry — a registry of instances can only hold
    pre-configured ones. The `by-ids` registration held an empty
    list and was removed on 2026-08-29 for that reason: an
    instance selecting nothing, under a name nobody could use.

    **What this delivers is ADR-0003's delegation, exercised.**
    The engine holds a `SelectionStrategy` and no criterion; the
    criterion is the strategy. Until 2026-08-29 that had been
    true of the code and asserted by nothing running.
    """

    engine = SelectionEngine()

    return engine.select(
        view=view,
        selection_id=selection_id,
        strategy=ByIdsSelectionStrategy(selected_ids),
        metadata=metadata,
    )
