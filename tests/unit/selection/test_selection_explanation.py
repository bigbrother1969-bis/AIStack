from pathlib import Path

import pytest

from aistack.catalog.filesystem import MediaLibraryCatalogBuilder
from aistack.kernel.catalog import Catalog
from aistack.providers.filesystem import MediaLibraryProvider
from aistack.selection.explanation import explain_selection
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


def by_id(catalog: Catalog, selected_ids: list[str]) -> dict[str, object]:
    resolution = resolve_subtrees(catalog, selected_ids)

    return {
        decision.id: decision
        for decision in explain_selection(catalog, resolution)
    }


def test_every_catalog_item_gets_a_decision(catalog):
    """
    `STD-0300` VS-3 criterion 3.2, read literally: *every* included
    and excluded item, not only the ones that were ticked.
    `Selection` never represented an excluded item at all — this is
    the gap, closed by walking `catalog.items` rather than the
    selection.
    """

    decisions = by_id(catalog, ["Classique"])

    assert set(decisions) == {item.id for item in catalog.items}


def test_a_ticked_root_is_ruled_ticked(catalog):
    decisions = by_id(catalog, ["Classique"])

    assert decisions["Classique"].included is True
    assert decisions["Classique"].rule == "ticked"


def test_a_descendant_of_a_ticked_root_is_ruled_inherited(catalog):
    decisions = by_id(catalog, ["Classique"])

    assert decisions["Classique/Bach"].included is True
    assert decisions["Classique/Bach"].rule == "inherited from 'Classique'"

    assert decisions["Classique/Berlioz"].included is True
    assert decisions["Classique/Berlioz"].rule == "inherited from 'Classique'"


def test_an_untouched_item_is_ruled_excluded(catalog):
    """
    `AC  DC` was never ticked and has no ticked ancestor — the
    case `Selection` gave no trace to explain at all.
    """

    decisions = by_id(catalog, ["Classique"])

    assert decisions["AC  DC"].included is False
    assert decisions["AC  DC"].rule == (
        "excluded, never ticked and no ticked ancestor"
    )
    assert decisions["AC  DC/Back in Black"].included is False


def test_a_ticked_descendant_of_a_ticked_ancestor_is_ruled_redundant(catalog):
    """
    Ticking `Classique` and `Classique/Bach` is not an error
    (`SubtreeResolution`'s own documentation), and it is still
    included — but the rule that decided it differs from a plain
    inheritance: it says the tick was redundant, and names what
    already covered it.
    """

    decisions = by_id(catalog, ["Classique", "Classique/Bach"])

    assert decisions["Classique/Bach"].included is True
    assert decisions["Classique/Bach"].rule == (
        "redundant, already covered by 'Classique'"
    )


def test_an_absent_ticked_identifier_is_not_a_catalog_item_to_explain(catalog):
    """
    `SubtreeResolution.absent` already names identifiers the
    catalog no longer holds. They are not in `catalog.items`, so
    there is nothing here to attach a decision to — this asserts
    the count stays exactly the catalog's own, not the catalog's
    plus a phantom entry for the ghost identifier.
    """

    decisions = by_id(catalog, ["Classique", "gone/nonexistent"])

    assert len(decisions) == len(catalog.items)
    assert "gone/nonexistent" not in decisions


def test_nothing_ticked_leaves_every_item_excluded(catalog):
    decisions = by_id(catalog, [])

    assert all(not decision.included for decision in decisions.values())
    assert all(
        decision.rule == "excluded, never ticked and no ticked ancestor"
        for decision in decisions.values()
    )
