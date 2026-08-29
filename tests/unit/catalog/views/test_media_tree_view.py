from pathlib import Path

import pytest

from aistack.catalog.filesystem import MediaLibraryCatalogBuilder
from aistack.catalog.views.media import MediaTreeViewEngine
from aistack.kernel.bootstrap import create_kernel
from aistack.kernel.catalog import Catalog, CatalogItem
from aistack.providers.filesystem import MediaLibraryProvider


def write(path: Path, size: int = 1) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * size)
    return path


@pytest.fixture
def view(tmp_path: Path):
    root = tmp_path / "library"

    write(root / "Abd Al Malik" / "Gibraltar" / "01.mp3", 5)
    write(root / "AC  DC" / "Back in Black" / "01.mp3", 5)
    write(root / "AC  DC" / "loose.mp3", 5)
    write(root / "Classique" / "Bach" / "Cantates" / "01.mp3", 5)
    write(root / "Classique" / "Berlioz" / "01.mp3", 5)
    write(root / "The Beatles" / "01.mp3", 5)
    write(root / "soum bill" / "01.mp3", 5)

    catalog = MediaLibraryCatalogBuilder(
        catalog_id="music-library",
        title="Music Library",
    ).build(MediaLibraryProvider(root).collect())

    return MediaTreeViewEngine().build(catalog)


def order(view) -> list[str]:
    return [item.id for item in view.items]


def test_every_parent_comes_immediately_before_its_own_descendants(view):
    """
    Depth-first is what turns 2393 flat identifiers into something
    a person can walk — measured on the owner's library,
    2026-08-29. Alphabetically flat, `Classique/Bach/Cantates`
    would sit between `Classique/Bach` and `Classique/Berlioz` by
    accident of spelling; here it sits there by belonging, and
    `Classique/Berlioz` comes after the whole of Bach.
    """

    assert order(view) == [
        "Abd Al Malik",
        "Abd Al Malik/Gibraltar",
        "AC  DC",
        "AC  DC/Back in Black",
        "Classique",
        "Classique/Bach",
        "Classique/Bach/Cantates",
        "Classique/Berlioz",
        "soum bill",
        "The Beatles",
    ]


def test_siblings_are_ordered_without_regard_to_case(view):
    """
    Comparing code points puts every capital before every
    lowercase letter. In the owner's library listed that way,
    `soum bill` is exiled past `Vidéos` to the very end, after two
    hundred capitalised artists — which is exactly what his
    terminal shows him today.

    Case-folded, it comes back among the S's, before `The
    Beatles`. The raw label is the tie-breaker so the order stays
    total, and no locale is consulted so two hosts holding the
    same library agree — STD-0300 § 6.
    """

    identifiers = order(view)

    assert identifiers.index("soum bill") < identifiers.index("The Beatles")

    assert sorted(["soum bill", "The Beatles"]) == [
        "The Beatles",
        "soum bill",
    ]


def test_the_order_is_stable_across_two_builds(view, tmp_path: Path):

    again = MediaTreeViewEngine().build(
        MediaLibraryCatalogBuilder(
            catalog_id="music-library",
            title="Music Library",
        ).build(MediaLibraryProvider(tmp_path / "library").collect())
    )

    assert order(again) == order(view)


def test_a_node_says_whether_it_has_children(view):
    """
    So the surface can draw a fold control in one pass, without
    looking ahead in the list.

    `AC  DC` holds an album *and* a loose track — seventeen
    directories in the owner's library are both at once. It is a
    parent and a leaf, and the two facts are carried separately.
    """

    entries = {item.id: item for item in view.items}

    assert entries["AC  DC"].metadata["has_children"] == "True"
    assert entries["AC  DC"].metadata["media_files"] == "1"

    assert entries["Classique/Berlioz"].metadata["has_children"] == "False"


def test_the_weight_and_the_depth_travel_to_the_surface(view):

    entries = {item.id: item for item in view.items}

    assert entries["Classique"].metadata["depth"] == "1"
    assert entries["Classique"].metadata["total_media_files"] == "2"
    assert entries["Classique"].metadata["total_media_bytes"] == "10"

    assert entries["Classique/Bach/Cantates"].metadata["depth"] == "3"


def test_the_view_carries_where_it_was_read_and_what_was_left_out(view):
    """
    The UI runs on a host nobody reviewing this code can observe.
    What the screen displays about itself is the only instrument
    both sides share.
    """

    assert view.metadata["root"].endswith("library")
    assert view.metadata["exists"] == "True"
    assert view.metadata["node_count"] == str(len(view.items))
    assert "unrecognized_extensions" in view.metadata


def test_a_node_whose_parent_is_absent_is_shown_and_not_dropped():
    """
    A catalog from `MediaLibraryCatalogBuilder` cannot produce
    this: a node holds media below it, so every ancestor does, so
    every ancestor is a node. The engine does not rely on that.

    A view that silently omitted what it could not place would
    hide the one thing worth seeing, and this heritage has paid
    for that shape more than once — most recently in a provider
    where an unrecognised file left no trace.
    """

    catalog = Catalog(
        catalog_id="orphan",
        title="Orphan",
        items=(
            CatalogItem(
                id="Ghost/Album",
                label="Album",
                kind="directory",
                metadata={"parent": "Ghost", "depth": "2"},
            ),
        ),
    )

    view = MediaTreeViewEngine().build(catalog)

    assert order(view) == ["Ghost/Album"]


def test_the_engine_is_retrieved_from_the_kernel_by_its_identifier():
    """
    Which view a surface shows is governed data, not a class named
    in application code — ADR-0002 § *Decision*. The engine is
    registered where `MediaLibraryProvider` is not, because it
    carries no configuration: a registry of instances can only
    hold pre-configured ones, which is what the `by-ids`
    registration failed to be and why it was removed on
    2026-08-29.
    """

    engine = create_kernel().registries.catalog_views.get("media-tree")

    assert isinstance(engine, MediaTreeViewEngine)
