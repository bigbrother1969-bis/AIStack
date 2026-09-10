from __future__ import annotations

from dataclasses import dataclass

from aistack.architecture.graph import ArchitectureGraph

FULL_VIEW = "all"


@dataclass(frozen=True)
class ArchitectureView:
    """
    One named slice of the graph — the whole thing, or one category.

    Step 5 (`claude/PLAN-J2-ARCHITECTURE-HTML-2026-09-10.md`) is what
    turns a view into `.mmd` text and a place in the rendered HTML's
    own view selector; this is only the slice itself.
    """

    name: str
    graph: ArchitectureGraph


def available_view_names(graph: ArchitectureGraph) -> tuple[str, ...]:
    """
    Every view this graph can produce, `FULL_VIEW` first, then one per
    category — in the categorization's own declared order.

    **Nothing here names a category.** The pre-AIStack system's own
    `generate_mermaid_views.py` was six functions, one written by hand
    per category, so renaming or adding a category meant editing code.
    This reads the names straight off `graph.categories` — itself
    built from `ServiceCategorizationDefinition`
    (`src/aistack/architecture/definitions/service_categorization.yml`)
    — so the declared file is still the one place a category is
    named, the same discipline `ServiceCategorizationDefinition`
    itself was ported for (GOV-P-001).
    """

    return (FULL_VIEW,) + tuple(category.name for category in graph.categories)


def build_view(graph: ArchitectureGraph, name: str) -> ArchitectureView:
    """
    Filter the full graph down to one named view.

    **One function, not one per category** — the generalization
    `claude/PLAN-J2-ARCHITECTURE-HTML-2026-09-10.md` step 4 asks for,
    in place of `generate_mermaid_views.py`'s six hand-written
    filters. `FULL_VIEW` returns the graph unfiltered (the old
    system's own master `architecture.mmd`); any other name is
    matched against `graph.categories` by exact name.

    Raises `ValueError` naming the available views rather than
    returning an empty one — an empty view and an unknown name look
    identical to whatever renders it, and only this function still
    knows which one happened.
    """

    if name == FULL_VIEW:
        return ArchitectureView(name=FULL_VIEW, graph=graph)

    matching = tuple(
        category for category in graph.categories if category.name == name
    )

    if not matching:
        available = ", ".join(available_view_names(graph))
        raise ValueError(f"Unknown view {name!r}; available: {available}")

    return ArchitectureView(name=name, graph=ArchitectureGraph(categories=matching))


def build_all_views(graph: ArchitectureGraph) -> tuple[ArchitectureView, ...]:
    """
    Every view `available_view_names` names, built in that same order
    — the whole selector step 5's HTML wrapper will offer, computed
    once rather than view by view.
    """

    return tuple(
        build_view(graph, name) for name in available_view_names(graph)
    )
