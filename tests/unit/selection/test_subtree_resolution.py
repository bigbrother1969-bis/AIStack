from pathlib import Path

import pytest

from aistack.catalog.filesystem import MediaLibraryCatalogBuilder
from aistack.kernel.catalog import Catalog, CatalogItem
from aistack.providers.filesystem import MediaLibraryProvider
from aistack.selection.subtree import resolve_subtrees


def write(path: Path, size: int = 1) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * size)
    return path


@pytest.fixture
def catalog(tmp_path: Path) -> Catalog:
    root = tmp_path / "library"

    write(root / "Classique" / "Bach" / "Cantates" / "01.mp3", 100)
    write(root / "Classique" / "Berlioz" / "01.mp3", 200)
    write(root / "AC  DC" / "Back in Black" / "01.mp3", 400)
    write(root / "AC  DC" / "loose.mp3", 50)

    return MediaLibraryCatalogBuilder(
        catalog_id="music-library",
        title="Music Library",
    ).build(MediaLibraryProvider(root).collect())


def test_a_ticked_node_designates_its_whole_subtree(catalog):
    """
    The owner's decision of 2026-08-29: an identifier designates a
    subtree, at the height the human ticked. Ticking `Classique`
    takes Bach, Berlioz and the Cantates with it.
    """

    resolution = resolve_subtrees(catalog, ["Classique"])

    assert resolution.roots == ("Classique",)

    assert resolution.covered == (
        "Classique",
        "Classique/Bach",
        "Classique/Bach/Cantates",
        "Classique/Berlioz",
    )

    assert resolution.media_files == 2
    assert resolution.media_bytes == 300


def test_a_parent_and_its_child_are_counted_once(catalog):
    """
    The case that makes a naive sum wrong, and the reason `roots`
    exists. Ticking `Classique` and `Classique/Bach` must weigh
    what `Classique` weighs — 300 bytes here, not 400.

    On a 64 Go quota, a capacity bar that double-counts is worse
    than no capacity bar: it refuses selections that fit.
    """

    resolution = resolve_subtrees(catalog, ["Classique", "Classique/Bach"])

    assert resolution.roots == ("Classique",)
    assert resolution.redundant == ("Classique/Bach",)

    assert resolution.media_bytes == 300
    assert resolution.media_files == 2


def test_a_redundant_tick_is_reported_and_not_dropped(catalog):
    """
    Ticking a parent then its child is not an error and nothing is
    removed. It is worth saying: unticking the parent would leave
    the child behind, and the human should be able to see that
    before it happens.
    """

    resolution = resolve_subtrees(
        catalog, ["Classique", "Classique/Bach/Cantates"]
    )

    assert resolution.redundant == ("Classique/Bach/Cantates",)
    assert "Classique/Bach/Cantates" in resolution.covered


def test_two_disjoint_ticks_add_up(catalog):

    resolution = resolve_subtrees(catalog, ["Classique/Berlioz", "AC  DC"])

    assert resolution.roots == ("AC  DC", "Classique/Berlioz")

    assert resolution.media_files == 3
    assert resolution.media_bytes == 650


def test_a_deleted_directory_is_selected_but_absent(catalog):
    """
    The library is scanned at every request — decided 2026-08-29 —
    so a directory deleted on the server leaves the catalog while
    staying in the saved selection.

    It must be shown as *selected but absent*: ignoring it in
    silence loses a tick the human made, and letting the generator
    discover it later fails far from the screen that could explain
    it.
    """

    resolution = resolve_subtrees(catalog, ["Classique", "Gone/For Good"])

    assert resolution.absent == ("Gone/For Good",)
    assert resolution.roots == ("Classique",)
    assert resolution.media_bytes == 300


def test_the_same_identifier_ticked_twice_is_one_tick(catalog):
    """
    A form posts what the browser sends. Nothing guarantees it
    sends each identifier once.
    """

    resolution = resolve_subtrees(catalog, ["AC  DC", "AC  DC"])

    assert resolution.roots == ("AC  DC",)
    assert resolution.media_bytes == 450


def test_nothing_ticked_designates_nothing(catalog):

    resolution = resolve_subtrees(catalog, [])

    assert resolution.roots == ()
    assert resolution.covered == ()
    assert resolution.media_files == 0
    assert resolution.media_bytes == 0


def test_ancestry_is_read_from_the_declared_parent_not_the_path():
    """
    Splitting the identifier on the separator would agree with the
    declared parent in every catalog this library has produced,
    and would stop agreeing the day an identifier is not a path —
    the second member of the family the owner decided on
    2026-08-29.

    Here the identifiers look nested and the declared parents say
    they are not. The resolution follows what is declared: two
    roots, nothing redundant, both weights counted.
    """

    catalog = Catalog(
        catalog_id="declared",
        title="Declared",
        items=(
            CatalogItem(
                id="a/b",
                label="b",
                metadata={
                    "parent": "",
                    "total_media_files": "1",
                    "total_media_bytes": "10",
                },
            ),
            CatalogItem(
                id="a/b/c",
                label="c",
                metadata={
                    "parent": "",
                    "total_media_files": "1",
                    "total_media_bytes": "20",
                },
            ),
        ),
    )

    resolution = resolve_subtrees(catalog, ["a/b", "a/b/c"])

    assert resolution.roots == ("a/b", "a/b/c")
    assert resolution.redundant == ()
    assert resolution.media_bytes == 30


def test_a_parent_chain_that_closes_on_itself_does_not_hang():
    """
    Not something `MediaLibraryCatalogBuilder` can produce, and
    not something worth hanging an interface for either. A screen
    that stops responding says nothing; one that renders a wrong
    weight can be read and corrected.
    """

    catalog = Catalog(
        catalog_id="loop",
        title="Loop",
        items=(
            CatalogItem(
                id="x",
                label="x",
                metadata={"parent": "y", "total_media_bytes": "1"},
            ),
            CatalogItem(
                id="y",
                label="y",
                metadata={"parent": "x", "total_media_bytes": "1"},
            ),
        ),
    )

    resolution = resolve_subtrees(catalog, ["x"])

    assert resolution.roots == ("x",)


def test_a_malformed_count_is_read_as_zero_rather_than_raised():
    """
    Metadata is text. The screen must still render: a weight that
    is wrong is visible where a stack trace is not.
    """

    catalog = Catalog(
        catalog_id="broken",
        title="Broken",
        items=(
            CatalogItem(
                id="odd",
                label="odd",
                metadata={
                    "parent": "",
                    "total_media_files": "many",
                    "total_media_bytes": "",
                },
            ),
        ),
    )

    resolution = resolve_subtrees(catalog, ["odd"])

    assert resolution.media_files == 0
    assert resolution.media_bytes == 0
