from __future__ import annotations

from dataclasses import dataclass

from aistack.architecture.graph import ArchitectureGraph

FULL_VIEW = "all"


@dataclass(frozen=True)
class ArchitectureView:
    """One named slice of the graph: the whole graph, or one category."""

    name: str
    graph: ArchitectureGraph


def available_view_names(graph: ArchitectureGraph) -> tuple[str, ...]:
    """
    Every view this graph can produce: `FULL_VIEW` first, then one per
    category in declared order. Category names come from the
    categorization file, never from code.
    """

    return (FULL_VIEW,) + tuple(category.name for category in graph.categories)


def build_view(graph: ArchitectureGraph, name: str) -> ArchitectureView:
    """
    Filter the full graph down to one named view.

    `FULL_VIEW` returns the graph unfiltered; any other name must match a
    category exactly. An unknown name raises `ValueError` listing the
    available views, rather than returning an empty view.
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
    """Every view `available_view_names` names, in the same order."""

    return tuple(
        build_view(graph, name) for name in available_view_names(graph)
    )
