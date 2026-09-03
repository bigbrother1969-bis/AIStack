from pathlib import Path

import pytest

from aistack.catalog.filesystem import MediaLibraryCatalogBuilder
from aistack.generators.filesystem.hardlink import (
    materialise_by_hardlink,
    SYNC_ARTEFACTS,
)
from aistack.providers.filesystem import (
    DEFAULT_MEDIA_EXTENSIONS,
    MediaLibraryProvider,
)
from aistack.selection.capacity import assess_capacity
from aistack.selection.subtree import resolve_subtrees


def write(path: Path, content: bytes = b"x") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


@pytest.fixture
def library(tmp_path: Path) -> Path:
    root = tmp_path / "library"

    write(root / "Classique" / "Bach" / "01.mp3", b"bach")
    write(root / "Classique" / "Bach" / "cover.jpg", b"image")
    write(root / "Classique" / "Berlioz" / "01.mp3", b"berlioz")
    write(root / "AC  DC" / "Back in Black" / "01.mp3", b"acdc")

    return root


@pytest.fixture
def target(tmp_path: Path) -> Path:
    return tmp_path / "android"


def catalog_of(root: Path):
    return MediaLibraryCatalogBuilder(
        catalog_id="music-library",
        title="Music Library",
    ).build(MediaLibraryProvider(root).collect())


def materialise(root: Path, target: Path, ticked, quota: int = 0, **kwargs):
    catalog = catalog_of(root)

    resolution = resolve_subtrees(catalog, ticked)

    return materialise_by_hardlink(
        catalog=catalog,
        resolution=resolution,
        capacity=assess_capacity(resolution, quota),
        target_root=target,
        media_extensions=DEFAULT_MEDIA_EXTENSIONS,
        **kwargs,
    )


def files_under(root: Path) -> set[str]:
    return {
        str(path.relative_to(root))
        for path in root.rglob("*")
        if path.is_file()
    }


def test_the_structure_is_mirrored_and_only_the_media_travel(
    library, target
):
    """
    Audio only, decided 2026-08-29 by the owner after the weights
    were measured: 176,1 Gio of audio, 0,7 of images, and 5,2 of
    files that are neither — unfinished downloads, archives, an
    executable and a DLL. `cover.jpg` stays where it is.
    """

    materialise(library, target, ["Classique"])

    assert files_under(target) == {
        "Classique/Bach/01.mp3",
        "Classique/Berlioz/01.mp3",
    }


def test_a_materialised_file_is_the_same_file_as_its_source(
    library, target
):
    """
    A hard link, not a copy: one inode, two names, no bytes spent.
    On the owner's library that is up to 60 Gio not duplicated on
    the volume the library already fills.
    """

    materialise(library, target, ["Classique/Bach"])

    source = library / "Classique" / "Bach" / "01.mp3"
    linked = target / "Classique" / "Bach" / "01.mp3"

    assert linked.stat().st_ino == source.stat().st_ino
    assert linked.read_bytes() == b"bach"


def test_a_second_run_writes_nothing(library, target):
    """
    Incremental, and that is not an optimisation. The generator
    this replaces emptied the target and rewrote it at every call
    — 118 Gio on the owner's library, and Syncthing propagating
    the deletion then the re-appearance to a phone over a VPN.

    A selection that did not change must cost no write, so that
    Syncthing sees nothing at all.
    """

    materialise(library, target, ["Classique"])

    report = materialise(library, target, ["Classique"])

    assert report.linked == ()
    assert report.removed == ()
    assert report.unchanged == 2


def test_unticking_removes_what_is_no_longer_designated(library, target):
    """
    Désynchronisation, in the owner's words: unticking is what
    takes a directory off the phone. Syncthing propagates the
    removal, which is the whole mechanism.
    """

    materialise(library, target, ["Classique"])

    report = materialise(library, target, ["Classique/Bach"])

    assert report.removed == ("Classique/Berlioz/01.mp3",)

    assert files_under(target) == {"Classique/Bach/01.mp3"}


def test_a_directory_left_empty_is_pruned(library, target):
    """
    A folder emptied of its tracks but still present is a node the
    phone keeps showing and the screen no longer knows about.
    Nothing here decides a directory is unwanted: it notices that
    nothing is left inside.
    """

    materialise(library, target, ["Classique"])

    report = materialise(library, target, ["Classique/Bach"])

    assert "Classique/Berlioz" in report.pruned

    assert not (target / "Classique" / "Berlioz").exists()


def test_a_replaced_source_is_relinked_rather_than_left_stale(
    library, target
):
    """
    The one failure mode of the hard link, closed by measuring it.
    A tag editor that *replaces* a file instead of editing it in
    place leaves the target pointing at the old content, and
    nothing about the target would say so.
    """

    materialise(library, target, ["Classique/Bach"])

    source = library / "Classique" / "Bach" / "01.mp3"
    source.unlink()
    write(source, b"re-ripped")

    report = materialise(library, target, ["Classique/Bach"])

    assert report.relinked == ("Classique/Bach/01.mp3",)

    linked = target / "Classique" / "Bach" / "01.mp3"

    assert linked.read_bytes() == b"re-ripped"
    assert linked.stat().st_ino == source.stat().st_ino


def test_the_synchronisation_artefacts_are_preserved(library, target):
    """
    `.stfolder` is how Syncthing recognises a folder it manages;
    removing it stops the folder syncing.

    Preserved at any depth, not only at the top. The previous
    generator preserved it at the root because it never descended,
    and a rule that holds by accident breaks when the accident
    stops.
    """

    target.mkdir(parents=True)
    write(target / ".stfolder" / "marker", b"")
    write(target / "Classique" / ".stignore", b"")

    materialise(library, target, ["Classique/Bach"])

    assert (target / ".stfolder" / "marker").exists()
    assert (target / "Classique" / ".stignore").exists()

    assert ".stfolder" in SYNC_ARTEFACTS


def test_a_dry_run_writes_nothing_and_says_what_it_would_do(
    library, target
):
    """
    The first run of this against a real library is irreversible
    in practice: Syncthing carries whatever happens to the phone
    within seconds. On 2026-07-13 a generator emptied that folder
    and stopped part way, and nobody could have seen it coming.
    """

    report = materialise(library, target, ["Classique"], dry_run=True)

    assert report.dry_run is True

    assert report.linked == (
        "Classique/Bach/01.mp3",
        "Classique/Berlioz/01.mp3",
    )

    assert not target.exists()


def test_a_dry_run_reports_no_pruning(library, target):
    """
    Nothing was removed, so nothing is empty that was not already.
    Reporting today's empty directories as *would be pruned* would
    be a claim about a state that does not exist.
    """

    materialise(library, target, ["Classique"])

    report = materialise(library, target, ["Classique/Bach"], dry_run=True)

    assert report.pruned == ()
    assert (target / "Classique" / "Berlioz" / "01.mp3").exists()


def test_a_target_on_another_filesystem_is_refused_before_any_write(
    library, target
):
    """
    A hard link cannot cross a filesystem, and the error a failed
    link raises names a file rather than the reason. The refusal
    names the reason.

    The comparison is made against the nearest existing ancestor
    of the target, so the answer arrives before a directory is
    created on a disk that could never have held the links.
    """

    catalog = catalog_of(library)

    resolution = resolve_subtrees(catalog, ["Classique"])

    report = materialise_by_hardlink(
        catalog=catalog,
        resolution=resolution,
        capacity=assess_capacity(resolution, 0),
        target_root=Path("/proc/aistack-elsewhere"),
        media_extensions=DEFAULT_MEDIA_EXTENSIONS,
    )

    assert "different filesystems" in report.refused
    assert report.linked == ()


def test_a_missing_library_root_is_refused_with_its_reason(
    tmp_path: Path, target
):
    """
    The root travels in the application definition and names a
    path on another machine. It will be wrong one day, and what
    the screen shows then has to be actionable.
    """

    catalog = catalog_of(tmp_path / "gone")

    resolution = resolve_subtrees(catalog, [])

    report = materialise_by_hardlink(
        catalog=catalog,
        resolution=resolution,
        capacity=assess_capacity(resolution, 0),
        target_root=target,
        media_extensions=DEFAULT_MEDIA_EXTENSIONS,
    )

    assert "library root does not exist" in report.refused
    assert not target.exists()


def test_a_node_ticked_twice_over_materialises_its_files_once(
    library, target
):
    """
    Ticking `Classique` and `Classique/Bach` designates the same
    files through two ticks. The resolution counts them once and
    the materialisation writes them once.
    """

    report = materialise(
        library, target, ["Classique", "Classique/Bach"]
    )

    assert len(report.linked) == 2

    assert files_under(target) == {
        "Classique/Bach/01.mp3",
        "Classique/Berlioz/01.mp3",
    }


def test_an_absent_tick_does_not_stop_what_exists(library, target):
    """
    A directory deleted on the server leaves the catalog and stays
    in the saved selection. The resolution reports it as absent
    and the screen shows it; the materialisation carries on with
    what is there rather than refusing the whole selection.
    """

    report = materialise(library, target, ["Classique/Bach", "Gone"])

    assert report.linked == ("Classique/Bach/01.mp3",)
