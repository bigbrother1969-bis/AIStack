from pathlib import Path

import pytest

from aistack.catalog.filesystem import MediaLibraryCatalogBuilder
from aistack.generators.filesystem.hardlink import materialise_by_hardlink
from aistack.providers.filesystem import (
    DEFAULT_MEDIA_EXTENSIONS,
    MediaLibraryProvider,
)
from aistack.selection.capacity import assess_capacity
from aistack.selection.materialisation_status import materialized_nodes
from aistack.selection.subtree import resolve_subtrees


def write(path: Path, size: int = 1) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * size)
    return path


@pytest.fixture
def catalog(tmp_path: Path):
    root = tmp_path / "library"

    write(root / "Classique" / "Bach" / "01.mp3")
    write(root / "Classique" / "Berlioz" / "01.mp3")
    write(root / "AC  DC" / "loose.mp3")

    return MediaLibraryCatalogBuilder(
        catalog_id="music-library",
        title="Music Library",
    ).build(MediaLibraryProvider(root).collect())


def status(catalog, ticked, target_root):
    resolution = resolve_subtrees(catalog, ticked)

    report = materialise_by_hardlink(
        catalog=catalog,
        resolution=resolution,
        capacity=assess_capacity(resolution, 0),
        target_root=target_root,
        media_extensions=DEFAULT_MEDIA_EXTENSIONS,
        dry_run=True,
    )

    return materialized_nodes(report, resolution)


def test_a_node_with_nothing_yet_in_the_target_is_not_materialized(
    catalog, tmp_path: Path
):
    target = tmp_path / "target"

    assert "AC  DC" not in status(catalog, ["AC  DC"], target)


def test_a_node_already_linked_is_materialized(catalog, tmp_path: Path):
    target = tmp_path / "target"

    resolution = resolve_subtrees(catalog, ["AC  DC"])

    materialise_by_hardlink(
        catalog=catalog,
        resolution=resolution,
        capacity=assess_capacity(resolution, 0),
        target_root=target,
        media_extensions=DEFAULT_MEDIA_EXTENSIONS,
    )

    assert "AC  DC" in status(catalog, ["AC  DC"], target)


def test_an_organising_node_with_no_files_of_its_own_is_vacuously_materialized(
    catalog, tmp_path: Path
):
    """
    `Classique` holds no track directly — everything is under
    `Classique/Bach` and `Classique/Berlioz`. Nothing is declared
    for `Classique` itself, so nothing can be missing from it.
    """

    target = tmp_path / "target"

    assert "Classique" in status(catalog, ["Classique"], target)


def test_a_partially_linked_selection_leaves_only_the_incomplete_node_out(
    catalog, tmp_path: Path
):
    target = tmp_path / "target"

    resolution = resolve_subtrees(catalog, ["Classique/Bach"])

    materialise_by_hardlink(
        catalog=catalog,
        resolution=resolution,
        capacity=assess_capacity(resolution, 0),
        target_root=target,
        media_extensions=DEFAULT_MEDIA_EXTENSIONS,
    )

    result = status(catalog, ["Classique/Bach", "Classique/Berlioz"], target)

    assert "Classique/Bach" in result
    assert "Classique/Berlioz" not in result


def test_a_stale_inode_still_counts_as_present(catalog, tmp_path: Path):
    """
    `relinked` files are present on disk, only pointing at outdated
    content — the tag-editor case `materialise_by_hardlink` guards
    against. A file the phone can already see is not a file this
    function should call missing.
    """

    target = tmp_path / "target"

    resolution = resolve_subtrees(catalog, ["AC  DC"])

    materialise_by_hardlink(
        catalog=catalog,
        resolution=resolution,
        capacity=assess_capacity(resolution, 0),
        target_root=target,
        media_extensions=DEFAULT_MEDIA_EXTENSIONS,
    )

    stale = target / "AC  DC" / "loose.mp3"
    stale.unlink()
    stale.write_bytes(b"different content, different inode")

    assert "AC  DC" in status(catalog, ["AC  DC"], target)
