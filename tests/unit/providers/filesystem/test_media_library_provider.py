from pathlib import Path

import pytest

from aistack.providers.filesystem import (
    DEFAULT_MEDIA_EXTENSIONS,
    MediaLibraryProvider,
)


def write(path: Path, size: int = 1) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * size)
    return path


@pytest.fixture
def library(tmp_path: Path) -> Path:
    """
    A tree with every shape the owner's library actually has.

    Measured 2026-08-29 and reproduced rather than imagined: an
    artist with albums, an artist with loose tracks and no
    subdirectory, an artist with **both** — seventeen of those in
    the real library — a genre stacking composer then album, and
    two directories holding no media at all.
    """

    root = tmp_path / "library"

    write(root / "Artist A" / "Album 1" / "01.mp3", 100)
    write(root / "Artist A" / "Album 1" / "02.mp3", 100)
    write(root / "Artist A" / "Album 2" / "01.flac", 300)
    write(root / "Artist A" / "loose.mp3", 50)

    write(root / "Artist B" / "01.mp3", 10)
    write(root / "Artist B" / "02.mp3", 10)

    write(root / "Classique" / "Bach" / "Cantates" / "01.mp3", 7)

    write(root / "Covers" / "front.jpg", 999)

    (root / "lost+found").mkdir(parents=True)

    return root


def observed(root: Path, **kwargs) -> dict[str, dict]:
    collected = MediaLibraryProvider(root, **kwargs).collect()

    return {
        entry["relative_path"]: entry
        for entry in collected["library"]["directories"]
    }


def test_the_provider_reports_directories_that_hold_no_media(library):
    """
    A provider observes and does not qualify — FDN-0003 Article 4,
    and `RepositoryProvider` says it in the same words.

    `Covers` holds a JPEG and `lost+found` holds nothing. Both are
    reported, with a total of zero. Deciding they are not
    selectable nodes is the Catalog builder's rule, and a provider
    applying it here would hide from that builder the evidence the
    rule is written against.
    """

    entries = observed(library)

    assert entries["Covers"]["total_media_files"] == 0
    assert entries["lost+found"]["total_media_files"] == 0


def test_a_directory_carries_what_is_inside_it_and_what_is_below(library):
    """
    The two counts answer different questions, and the artist who
    keeps loose tracks beside albums is why both are needed.

    `Artist A` holds one track directly and four in total. A
    screen that showed only the total could not tell a container
    from a leaf; one that showed only the direct count could not
    say what ticking `Artist A` costs.
    """

    entries = observed(library)

    assert entries["Artist A"]["media_files"] == 1
    assert entries["Artist A"]["media_bytes"] == 50

    assert entries["Artist A"]["total_media_files"] == 4
    assert entries["Artist A"]["total_media_bytes"] == 550


def test_the_totals_roll_up_through_every_level(library):
    """
    `Classique/Bach/Cantates` is the shape that breaks a rule
    written for two levels: the media sit three deep and the two
    directories above hold none directly.
    """

    entries = observed(library)

    assert entries["Classique"]["media_files"] == 0
    assert entries["Classique"]["total_media_files"] == 1
    assert entries["Classique"]["total_media_bytes"] == 7

    assert entries["Classique/Bach"]["total_media_files"] == 1
    assert entries["Classique/Bach/Cantates"]["media_files"] == 1


def test_a_directory_knows_its_parent_and_its_depth(library):
    """
    The tree is a fact of the source, so the observation carries
    it. Rebuilding it from the identifiers would work until an
    identifier contains a separator for another reason.
    """

    entries = observed(library)

    assert entries["Artist A"]["parent"] == ""
    assert entries["Artist A"]["depth"] == 1

    assert entries["Classique/Bach"]["parent"] == "Classique"
    assert entries["Classique/Bach"]["depth"] == 2

    assert entries["Classique/Bach/Cantates"]["parent"] == "Classique/Bach"
    assert entries["Classique/Bach/Cantates"]["depth"] == 3


def test_what_is_not_media_is_not_counted(library):
    """
    `Covers/front.jpg` weighs more than every track in this tree
    put together. A capacity bar that counted it would be wrong by
    more than it is right.
    """

    entries = observed(library)

    assert entries["Covers"]["media_files"] == 0
    assert entries["Covers"]["media_bytes"] == 0


def test_the_extensions_are_the_caller_s_and_not_the_module_s(library):
    """
    Which extensions a library holds is deployment knowledge and
    travels in the application definition. The default exists so
    an unconfigured caller gets something; it decides nothing.
    """

    only_flac = observed(library, media_extensions=frozenset({".flac"}))

    assert only_flac["Artist A"]["total_media_files"] == 1
    assert only_flac["Artist B"]["total_media_files"] == 0

    assert ".flac" in DEFAULT_MEDIA_EXTENSIONS


def test_the_extensions_are_matched_whatever_their_case(tmp_path: Path):
    """
    `.MP3` is what a decade of ripping software wrote. A library
    assembled since 2009 has both.
    """

    root = tmp_path / "library"

    write(root / "Artist" / "01.MP3", 5)

    entries = observed(root, media_extensions=frozenset({".mp3"}))

    assert entries["Artist"]["media_files"] == 1


def test_the_order_does_not_depend_on_the_filesystem(library):
    """
    STD-0300 § 6 requires an unchanged input to produce an
    identical output. `os.walk` yields whatever order the
    filesystem hands it, and two hosts holding the same files hand
    back two different ones.
    """

    directories = MediaLibraryProvider(library).collect()["library"][
        "directories"
    ]

    paths = [entry["relative_path"] for entry in directories]

    assert paths == sorted(paths)


def test_a_link_inside_the_tree_is_skipped_and_counted(library):
    """
    A link is announced by the walk and never visited. Adding its
    target's weight would count the same tracks twice, and a link
    pointing upwards would not terminate.

    Counted rather than passed over in silence: a library that
    shrinks and says by how much is a measurement.
    """

    (library / "Artist B copy").symlink_to(library / "Artist B")

    collected = MediaLibraryProvider(library).collect()

    entries = {
        entry["relative_path"]: entry
        for entry in collected["library"]["directories"]
    }

    assert collected["library"]["symlinks_not_followed"] == 1
    assert "Artist B copy" not in entries

    assert entries[""]["total_media_files"] == 7


def test_a_missing_root_is_reported_rather_than_raised(tmp_path: Path):
    """
    The root travels in the definition and names a path on another
    machine. It will be wrong one day, and the screen has to say
    so instead of returning a stack trace.
    """

    collected = MediaLibraryProvider(tmp_path / "nowhere").collect()

    assert collected["library"]["exists"] is False
    assert collected["library"]["directories"] == []


def test_the_observation_names_the_provider_that_made_it(library):

    collected = MediaLibraryProvider(library).collect()

    assert collected["provider"]["id"] == (
        "aistack.provider.filesystem.media-library"
    )
    assert collected["library"]["root"] == str(library)
