import pytest

from aistack.architecture.graph import ArchitectureGraph, CategoryGraph, ServiceNode, ServiceStatus
from aistack.architecture.views import (
    FULL_VIEW,
    ArchitectureView,
    available_view_names,
    build_all_views,
    build_view,
)


def graph(*categories: CategoryGraph) -> ArchitectureGraph:
    return ArchitectureGraph(categories=tuple(categories))


def category(name: str, *services: ServiceNode) -> CategoryGraph:
    return CategoryGraph(name=name, services=tuple(services))


def service(name: str, category_name: str) -> ServiceNode:
    return ServiceNode(
        name=name,
        category=category_name,
        container=None,
        status=ServiceStatus.NO_CONTAINER,
    )


def test_available_view_names_starts_with_the_full_view():
    g = graph(
        category("Supervision", service("Beszel", "Supervision")),
        category("Développement", service("Gitea", "Développement")),
    )

    assert available_view_names(g) == (FULL_VIEW, "Supervision", "Développement")


def test_available_view_names_follows_the_categorizations_own_order():
    """
    Nothing here re-sorts the categories — the declared file's own
    order is the one place a category is named, the same discipline
    `ServiceCategorizationDefinition` was ported to preserve.
    """

    g = graph(
        category("Développement"),
        category("AIStack"),
        category("Supervision"),
    )

    assert available_view_names(g) == (
        FULL_VIEW,
        "Développement",
        "AIStack",
        "Supervision",
    )


def test_an_empty_graph_offers_only_the_full_view():
    assert available_view_names(graph()) == (FULL_VIEW,)


def test_the_full_view_returns_the_whole_graph_unfiltered():
    g = graph(
        category("Supervision", service("Beszel", "Supervision")),
        category("Développement", service("Gitea", "Développement")),
    )

    view = build_view(g, FULL_VIEW)

    assert isinstance(view, ArchitectureView)
    assert view.name == FULL_VIEW
    assert view.graph is g


def test_a_named_view_carries_only_its_own_category():
    g = graph(
        category("Supervision", service("Beszel", "Supervision")),
        category("Développement", service("Gitea", "Développement")),
    )

    view = build_view(g, "Supervision")

    assert view.name == "Supervision"
    assert len(view.graph.categories) == 1
    assert view.graph.categories[0].name == "Supervision"
    assert [s.name for s in view.graph.categories[0].services] == ["Beszel"]


def test_an_unknown_view_name_is_refused_and_names_what_is_available():
    g = graph(category("Supervision"), category("Développement"))

    with pytest.raises(ValueError, match="Unknown view 'Cloud'"):
        build_view(g, "Cloud")


def test_an_unknown_view_names_the_available_views_in_its_error():
    g = graph(category("Supervision"), category("Développement"))

    with pytest.raises(
        ValueError, match=r"available: all, Supervision, Développement"
    ):
        build_view(g, "Cloud")


def test_build_all_views_returns_one_per_available_name_in_order():
    g = graph(
        category("Supervision", service("Beszel", "Supervision")),
        category("Développement", service("Gitea", "Développement")),
    )

    views = build_all_views(g)

    assert [v.name for v in views] == [FULL_VIEW, "Supervision", "Développement"]
    assert len(views[0].graph.categories) == 2
    assert len(views[1].graph.categories) == 1
    assert len(views[2].graph.categories) == 1


def test_build_all_views_on_an_empty_graph_returns_only_the_full_view():
    views = build_all_views(graph())

    assert len(views) == 1
    assert views[0].name == FULL_VIEW
    assert views[0].graph.categories == ()


def test_the_real_categorization_produces_seven_views():
    """
    Six governed categories
    (`src/aistack/architecture/definitions/service_categorization.yml`)
    plus the full view — a regression against the real shipped file,
    the same discipline
    `test_the_real_categorization_joins_against_a_live_shaped_catalog_pair`
    already applies one layer down.
    """

    from pathlib import Path

    from aistack.architecture.graph import build_architecture_graph
    from aistack.architecture.yaml import load_service_categorization_yaml
    from aistack.kernel.catalog import Catalog

    repo_root = Path(__file__).resolve().parents[3]
    categorization = load_service_categorization_yaml(
        repo_root
        / "src"
        / "aistack"
        / "architecture"
        / "definitions"
        / "service_categorization.yml"
    )

    empty_catalog = Catalog(catalog_id="x", title="x", items=())
    real_graph = build_architecture_graph(categorization, empty_catalog, empty_catalog)

    views = build_all_views(real_graph)

    assert len(views) == 7
    assert views[0].name == FULL_VIEW
    assert [v.name for v in views[1:]] == [
        "Administration, Cloud & Utilitaires",
        "Supervision",
        "Divertissement & Bureau",
        "Téléchargements",
        "AIStack",
        "Développement",
    ]

    aistack_view = build_view(real_graph, "AIStack")
    assert [s.name for s in aistack_view.graph.categories[0].services] == [
        "Music Sync"
    ]
