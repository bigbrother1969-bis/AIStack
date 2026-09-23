import pytest

from aistack.package_manager.contracts.knowledge_package import (
    KnowledgePackage,
)
from aistack.package_manager.contracts.package_item import PackageItem
from aistack.package_manager.manager import DefaultPackageManager


def _package(
    package_id: str = "pkg-test",
    items: tuple[PackageItem, ...] | None = None,
) -> KnowledgePackage:

    if items is None:
        items = (
            PackageItem(
                target_path="doc.md",
                content="New paragraph.",
                rationale="test",
            ),
        )

    return KnowledgePackage(
        package_id=package_id,
        title="Test package",
        source="unit test",
        items=items,
    )


def test_receive_returns_a_well_formed_package():

    package = _package()

    received = DefaultPackageManager().receive(package)

    assert received is package


def test_receive_rejects_missing_package_id():

    package = _package(package_id="")

    with pytest.raises(ValueError):
        DefaultPackageManager().receive(package)


def test_receive_rejects_empty_items():

    package = _package(items=())

    with pytest.raises(ValueError):
        DefaultPackageManager().receive(package)


def test_receive_rejects_item_with_empty_target_path():

    package = _package(
        items=(
            PackageItem(
                target_path="",
                content="New paragraph.",
                rationale="test",
            ),
        )
    )

    with pytest.raises(ValueError):
        DefaultPackageManager().receive(package)


def test_inspect_reports_missing_target_file(tmp_path):

    package = _package(
        items=(
            PackageItem(
                target_path="missing.md",
                content="New paragraph.",
                rationale="test",
            ),
        )
    )

    notes = DefaultPackageManager().inspect(package, tmp_path)

    assert len(notes) == 1
    assert "missing.md" in notes[0]
    assert "does not exist" in notes[0]


def test_inspect_counts_anchor_occurrences(tmp_path):

    target = tmp_path / "doc.md"
    target.write_text(
        "# Title\n\n## Section\n\nBody.\n",
        encoding="utf-8",
    )

    package = _package(
        items=(
            PackageItem(
                target_path="doc.md",
                content="New paragraph.",
                rationale="test",
                anchor="## Section",
            ),
        )
    )

    notes = DefaultPackageManager().inspect(package, tmp_path)

    assert "found 1 time(s)" in notes[0]
