"""
ADR-0002 § *Implementation state*, row 9, and GOV-0002/OS-039's
surface half.

**The chain these tests drive had never run.** ADR-0002 decides
`Catalog → Catalog View Engine → consumer`; ADR-0003 decides that
the Selection Engine delegates to interchangeable strategies. Both
were implemented and neither was exercised: measured 2026-08-27,
`SelectionEngine` had 0 callers and 0 tests, and the one Catalog
View Engine was registered and retrieved by nothing.

The Selection UI is what closed it, and **the logic is tested here
rather than through the UI on purpose**. `selection_ui` is a
top-level package whose dependencies — `fastapi`, `starlette`,
`jinja2` — this project does not declare; `pyproject.toml`
declares `PyYAML` and nothing else. Testing the HTTP layer would
mean adding dependencies to the heritage, which ADR-0001 governs.
So the workflow was extracted, and the handlers are two lines
each.
"""

from __future__ import annotations

import pytest

from aistack.kernel.bootstrap import create_kernel
from aistack.kernel.catalog import Catalog, CatalogItem
from aistack.kernel.catalog.views import CatalogView
from aistack.selection.workflow import build_view, select_from_view


@pytest.fixture
def kernel():
    return create_kernel()


@pytest.fixture
def catalog() -> Catalog:
    return Catalog(
        catalog_id="music-library",
        title="Music Library",
        items=(
            CatalogItem(
                id="a",
                label="Album A",
                kind="album",
                source="/music/a",
                metadata={"relative_path": "a"},
            ),
            CatalogItem(
                id="b",
                label="Album B",
                kind="album",
                source="/music/b",
                metadata={"relative_path": "b"},
            ),
        ),
    )


def test_the_view_is_produced_by_an_engine_retrieved_by_identifier(
    kernel, catalog
):
    """
    The producer is governed data, not a class named in
    application code.

    `music-selection` had been registered since the registry
    existed and retrieved by nothing — `unused-registrations`
    published it at every projection. This is the retrieval.
    """

    view = build_view(kernel, catalog, "music-selection")

    assert isinstance(view, CatalogView)
    assert view.view_id == "music-selection"
    assert view.source_catalog_id == "music-library"
    assert [item.id for item in view.items] == ["a", "b"]


def test_the_view_carries_the_traceability_the_selection_records(
    kernel, catalog
):
    """
    `view_id` and `source_catalog_id` are the pair `SelectionCatalog`
    did not have, and the reason GOV-0002/OS-042 resolved the way
    it did on 2026-08-29. This asserts they survive as far as the
    Selection, which is where a reader would look for them.
    """

    view = build_view(kernel, catalog, "music-selection")

    selection = select_from_view(view, "music_android", ["a"])

    assert selection.catalog_id == "music-library"
    assert selection.metadata["source_view"] == "music-selection"


def test_the_selection_goes_through_the_engine_and_its_strategy(
    kernel, catalog
):
    """
    ADR-0003's delegation, exercised rather than asserted.

    The engine holds a `SelectionStrategy` and no criterion; the
    criterion is the strategy. `ByIdsSelectionStrategy` keeps only
    identifiers the view offers, so a stale identifier is dropped
    rather than carried into governed knowledge — which a hand-built
    `Selection` did not do.
    """

    view = build_view(kernel, catalog, "music-selection")

    selection = select_from_view(view, "music_android", ["b", "gone", "a"])

    assert selection.selection_id == "music_android"
    assert selection.selected_ids == ["a", "b"]


def test_metadata_from_the_surface_reaches_the_selection(kernel, catalog):
    """
    The surface's own facts — which file it read, who manages it —
    travel beside the engine's, and neither overwrites the other.
    """

    view = build_view(kernel, catalog, "music-selection")

    selection = select_from_view(
        view,
        "music_android",
        ["a"],
        metadata={"managed_by": "selection_ui"},
    )

    assert selection.metadata["managed_by"] == "selection_ui"
    assert selection.metadata["source_view"] == "music-selection"


def test_no_selection_strategy_is_registered(kernel):
    """
    Decided 2026-08-29 by the owner.

    `ByIdsSelectionStrategy([])` was registered as `by-ids` — an
    instance holding an empty list, so retrieving it yielded a
    strategy that selects nothing. It could not be retrieved
    usefully at all, because the strategy carries its identifiers
    in its constructor and a registry of instances can only hold
    pre-configured ones.

    **This test states the decision rather than the absence.** A
    registry that is empty because nobody got round to it and one
    that is empty because nothing belongs in it read identically
    from a report.
    """

    assert kernel.registries.selection_strategies.all() == {}


def test_the_strategy_returns_what_its_contract_declares(kernel, catalog):
    """
    `SelectionStrategy.select` declares `tuple[str, ...]` and the
    implementation returned `list[str]` until 2026-08-29.

    ADR-0003 recorded it on 2026-08-27 and left it: nothing
    consumed the chain, so nothing could be wrong. **Neither
    `contract-debt` nor `false-declarations` sees it** — both
    compare call shapes, not return types — so this is the only
    instrument there is.
    """

    from aistack.kernel.selection.strategies import ByIdsSelectionStrategy

    view = build_view(kernel, catalog, "music-selection")

    selected = ByIdsSelectionStrategy(["a"]).select(view)

    assert type(selected) is tuple
