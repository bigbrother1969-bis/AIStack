from aistack.package_manager.contracts.knowledge_package import (
    KnowledgePackage,
)
from aistack.package_manager.contracts.package_item import PackageItem


def test_package_item_defaults():

    item = PackageItem(
        target_path="docs/example.md",
        content="New paragraph.",
        rationale="test",
    )

    assert item.anchor is None
    assert item.position == "after"


def test_knowledge_package_carries_its_items():

    item = PackageItem(
        target_path="docs/example.md",
        content="New paragraph.",
        rationale="test",
        anchor="## Heading",
        position="before",
    )

    package = KnowledgePackage(
        package_id="pkg-test",
        title="Test package",
        source="unit test",
        items=(item,),
    )

    assert package.package_id == "pkg-test"
    assert package.items == (item,)
    assert package.items[0].anchor == "## Heading"
