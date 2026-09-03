from pathlib import Path

import pytest

from aistack.catalog.filesystem import MediaLibraryCatalogBuilder
from aistack.generators.filesystem.hardlink import materialise_by_hardlink
from aistack.providers.filesystem import (
    DEFAULT_MEDIA_EXTENSIONS,
    MediaLibraryProvider,
)
from aistack.selection.capacity import assess_capacity
from aistack.selection.subtree import resolve_subtrees


def write(path: Path, size: int = 1) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * size)
    return path


@pytest.fixture
def catalog(tmp_path: Path):
    root = tmp_path / "library"

    write(root / "Small" / "01.mp3", 100)
    write(root / "Large" / "01.mp3", 900)

    return MediaLibraryCatalogBuilder(
        catalog_id="music-library",
        title="Music Library",
    ).build(MediaLibraryProvider(root).collect())


def verdict(catalog, ticked, quota):
    return assess_capacity(resolve_subtrees(catalog, ticked), quota)


def test_a_selection_under_the_quota_fits(catalog):

    assessed = verdict(catalog, ["Small"], 1000)

    assert assessed.fits
    assert assessed.declared
    assert assessed.selected_bytes == 100
    assert assessed.remaining_bytes == 900
    assert assessed.overflow_bytes == 0
    assert assessed.percent_used == 10.0


def test_a_selection_exactly_at_the_quota_fits(catalog):
    """
    The boundary is inclusive. A quota is a capacity, not a
    threshold to stay under: 64 Go declared means 64 Go usable.
    """

    assessed = verdict(catalog, ["Small", "Large"], 1000)

    assert assessed.fits
    assert assessed.remaining_bytes == 0
    assert assessed.percent_used == 100.0


def test_an_overflow_says_how_much_has_to_come_off(catalog):
    """
    *How far over* is the number the owner acts on. His saved
    selection weighed 118 Gio against 64 Go on 2026-08-29 —
    nearly double, a selection to halve rather than a line to
    nudge, and a bar that clamped at "full" would have hidden
    which of the two it was.
    """

    assessed = verdict(catalog, ["Small", "Large"], 600)

    assert not assessed.fits
    assert assessed.remaining_bytes == -400
    assert assessed.overflow_bytes == 400
    assert round(assessed.percent_used, 1) == 166.7


def test_an_undeclared_quota_constrains_nothing_and_says_so(catalog):
    """
    The definition is written by hand: an absent line and a line
    reading `0` are the same accident. Neither may quietly become
    a quota of zero that refuses everything, and neither may
    pretend a capacity was declared.
    """

    assessed = verdict(catalog, ["Small", "Large"], 0)

    assert assessed.fits
    assert not assessed.declared
    assert assessed.declared_bytes == 0
    assert assessed.selected_bytes == 1000
    assert assessed.percent_used == 0.0


def test_a_negative_quota_is_read_as_undeclared(catalog):

    assert not verdict(catalog, ["Small"], -1).declared


def test_the_materialisation_refuses_an_overflowing_selection(
    catalog, tmp_path: Path
):
    """
    The same rule at the second moment, and the one that cannot be
    forgotten: the verdict is a parameter, so materialising
    without having weighed is not something a caller can express.

    Nothing is written, and the sentence carries the three numbers
    the owner needs — what was selected, what was declared, and
    the difference.
    """

    target = tmp_path / "target"

    resolution = resolve_subtrees(catalog, ["Small", "Large"])

    report = materialise_by_hardlink(
        catalog=catalog,
        resolution=resolution,
        capacity=assess_capacity(resolution, 600),
        target_root=target,
        media_extensions=DEFAULT_MEDIA_EXTENSIONS,
    )

    assert "larger than the declared capacity" in report.refused
    assert "400 bytes too many" in report.refused

    assert report.linked == ()
    assert not target.exists()


def test_the_capacity_is_refused_before_the_target_is_touched(
    catalog, tmp_path: Path
):
    """
    Ordered first among the refusals because it is the one a human
    can act on: the others describe a machine that is not set up
    as expected, this one describes a choice to revise.

    So it answers even when the target could never have worked
    either — no directory is created, nothing is probed.
    """

    resolution = resolve_subtrees(catalog, ["Small", "Large"])

    report = materialise_by_hardlink(
        catalog=catalog,
        resolution=resolution,
        capacity=assess_capacity(resolution, 600),
        target_root=Path("/proc/aistack-elsewhere"),
        media_extensions=DEFAULT_MEDIA_EXTENSIONS,
    )

    assert "larger than the declared capacity" in report.refused


def test_a_selection_that_fits_is_materialised(catalog, tmp_path: Path):

    target = tmp_path / "target"

    resolution = resolve_subtrees(catalog, ["Small"])

    report = materialise_by_hardlink(
        catalog=catalog,
        resolution=resolution,
        capacity=assess_capacity(resolution, 1000),
        target_root=target,
        media_extensions=DEFAULT_MEDIA_EXTENSIONS,
    )

    assert report.refused == ""
    assert len(report.linked) == 1
