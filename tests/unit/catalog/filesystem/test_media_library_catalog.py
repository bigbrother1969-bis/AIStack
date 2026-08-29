from pathlib import Path

import pytest

from aistack.catalog.filesystem import MediaLibraryCatalogBuilder
from aistack.providers.filesystem import MediaLibraryProvider


def write(path: Path, size: int = 1) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * size)
    return path


@pytest.fixture
def library(tmp_path: Path) -> Path:
    root = tmp_path / "library"

    write(root / "Artist A" / "Album 1" / "01.mp3", 100)
    write(root / "Artist A" / "loose.mp3", 50)

    write(root / "Classique" / "Bach" / "Cantates" / "01.mp3", 7)

    write(root / "Covers" / "front.jpg", 999)

    (root / "lost+found").mkdir(parents=True)

    return root


@pytest.fixture
def catalog(library: Path):
    return MediaLibraryCatalogBuilder(
        catalog_id="music-library",
        title="Music Library",
    ).build(MediaLibraryProvider(library).collect())


def identifiers(catalog) -> set[str]:
    return {item.id for item in catalog.items}


def item(catalog, identifier: str):
    return next(item for item in catalog.items if item.id == identifier)


def test_a_node_is_kept_when_media_lie_under_it(catalog):
    """
    The one rule. The owner's tree is five levels deep and its
    1949 media directories sit at all five, so the catalog names
    no level — it names the nodes, and the human ticks the one
    they mean. Decided 2026-08-29 by the owner.
    """

    assert "Artist A" in identifiers(catalog)
    assert "Artist A/Album 1" in identifiers(catalog)

    assert "Classique" in identifiers(catalog)
    assert "Classique/Bach" in identifiers(catalog)
    assert "Classique/Bach/Cantates" in identifiers(catalog)


def test_a_directory_with_no_media_under_it_is_not_a_node(catalog):
    """
    `Covers` and `lost+found` are excluded for the reason they do
    not belong — there is no music under them — and not by being
    named. A blacklist would need maintaining against a tree that
    changes, and would keep them out on the day they hold music.
    """

    assert "Covers" not in identifiers(catalog)
    assert "lost+found" not in identifiers(catalog)


def test_the_rule_admits_a_directory_the_day_it_holds_media(library):

    write(library / "Covers" / "hidden.mp3", 3)

    catalog = MediaLibraryCatalogBuilder(
        catalog_id="music-library",
        title="Music Library",
    ).build(MediaLibraryProvider(library).collect())

    assert "Covers" in identifiers(catalog)


def test_the_root_is_the_subject_and_not_an_entry(catalog):
    """
    A tick on the root would mean *everything*, and the owner's
    everything is 118 Gio against a declared quota of 64 Go —
    measured 2026-08-29. The root is what the catalog is about.
    """

    assert "" not in identifiers(catalog)


def test_an_identifier_is_a_path_relative_to_the_root(catalog, library):
    """
    So it survives a library that moves, and stays readable to the
    human who ticked it. The absolute path is deployment knowledge
    and travels in `source`, which changes with the host — the
    split the Docker catalog already makes.
    """

    entry = item(catalog, "Classique/Bach")

    assert entry.label == "Bach"
    assert entry.source == str(library / "Classique" / "Bach")
    assert entry.metadata["parent"] == "Classique"
    assert entry.metadata["depth"] == "2"


def test_both_counts_reach_the_catalog(catalog):
    """
    The cumulative count is what a capacity bar adds up; the
    direct one is what tells a container from a leaf. Seventeen
    directories in the owner's library are both at once, so
    neither can be dropped.
    """

    entry = item(catalog, "Artist A")

    assert entry.metadata["media_files"] == "1"
    assert entry.metadata["total_media_files"] == "2"
    assert entry.metadata["total_media_bytes"] == "150"


def test_the_catalog_carries_the_root_it_was_read_from(catalog, library):
    """
    The screen has to be able to show which library it is
    displaying. The UI runs on a machine nobody watching this code
    can observe, so what it read is the only thing that says where
    it read it.
    """

    assert catalog.metadata["root"] == str(library)
    assert catalog.metadata["exists"] == "True"
    assert catalog.metadata["source_provider"] == (
        "aistack.provider.filesystem.media-library"
    )


def test_the_catalog_is_named_by_its_caller(library):
    """
    `music_android.yml` is an instance, not *the* application —
    decided 2026-08-29. A builder that named its own catalog would
    have to be edited for the second one.
    """

    catalog = MediaLibraryCatalogBuilder(
        catalog_id="comics-library",
        title="Comics Library",
    ).build(MediaLibraryProvider(library).collect())

    assert catalog.catalog_id == "comics-library"
    assert catalog.title == "Comics Library"


def test_the_catalog_carries_what_no_rule_could_place(library):
    """
    A node missing because its format is unknown looks exactly
    like a node missing because it is empty. The census is the
    difference, and it has to reach the surface that displays the
    catalog — which runs on a machine nobody reviewing this code
    can observe.

    Heaviest first, because the format worth adding is the one
    with the most files behind it.
    """

    write(library / "Unknown" / "01.xyz", 1)
    write(library / "Unknown" / "02.xyz", 1)
    write(library / "Unknown" / "03.zzz", 1)

    catalog = MediaLibraryCatalogBuilder(
        catalog_id="music-library",
        title="Music Library",
    ).build(MediaLibraryProvider(library).collect())

    census = catalog.metadata["unrecognized_extensions"]

    assert census.startswith(".xyz=2 ")
    assert ".zzz=1" in census
    assert ".jpg=1" in census


def test_a_file_without_extension_is_named_in_the_census(library):
    """
    An empty string in a space-separated line is a hole. The
    census says `(none)` rather than producing `=3`.
    """

    write(library / "Unknown" / "README", 1)

    catalog = MediaLibraryCatalogBuilder(
        catalog_id="music-library",
        title="Music Library",
    ).build(MediaLibraryProvider(library).collect())

    assert "(none)=1" in catalog.metadata["unrecognized_extensions"]
