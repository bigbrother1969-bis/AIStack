from aistack.package_manager.contracts.knowledge_package import (
    KnowledgePackage,
)
from aistack.package_manager.contracts.package_item import PackageItem
from aistack.package_manager.validation_engine import (
    DefaultValidationEngine,
)


def _package(items: tuple[PackageItem, ...]) -> KnowledgePackage:

    return KnowledgePackage(
        package_id="pkg-test",
        title="Test package",
        source="unit test",
        items=items,
    )


def test_missing_target_file_is_rejected(tmp_path):

    package = _package(
        (
            PackageItem(
                target_path="missing.md",
                content="New paragraph.",
                rationale="test",
            ),
        )
    )

    result = DefaultValidationEngine().validate(package, tmp_path)

    assert result.accepted is False
    assert result.findings[0].passed is False
    assert "does not exist" in result.findings[0].message


def test_missing_anchor_is_rejected(tmp_path):

    target = tmp_path / "doc.md"
    target.write_text("# Title\n\nBody.\n", encoding="utf-8")

    package = _package(
        (
            PackageItem(
                target_path="doc.md",
                content="New paragraph.",
                rationale="test",
                anchor="## Section",
            ),
        )
    )

    result = DefaultValidationEngine().validate(package, tmp_path)

    assert result.accepted is False
    assert "not found" in result.findings[0].message


def test_ambiguous_anchor_is_rejected(tmp_path):

    target = tmp_path / "doc.md"
    target.write_text(
        "# Title\n\n## Section\n\nBody.\n\n## Section\n\nMore.\n",
        encoding="utf-8",
    )

    package = _package(
        (
            PackageItem(
                target_path="doc.md",
                content="New paragraph.",
                rationale="test",
                anchor="## Section",
            ),
        )
    )

    result = DefaultValidationEngine().validate(package, tmp_path)

    assert result.accepted is False
    assert "ambiguous" in result.findings[0].message


def test_duplicate_content_is_rejected(tmp_path):

    target = tmp_path / "doc.md"
    target.write_text(
        "# Title\n\n## Section\n\nAlready there.\n",
        encoding="utf-8",
    )

    package = _package(
        (
            PackageItem(
                target_path="doc.md",
                content="Already there.",
                rationale="test",
                anchor="## Section",
            ),
        )
    )

    result = DefaultValidationEngine().validate(package, tmp_path)

    assert result.accepted is False
    assert "duplicate" in result.findings[0].message


def test_well_formed_item_is_accepted(tmp_path):

    target = tmp_path / "doc.md"
    target.write_text(
        "# Title\n\n## Section\n\nBody.\n",
        encoding="utf-8",
    )

    package = _package(
        (
            PackageItem(
                target_path="doc.md",
                content="New paragraph.",
                rationale="test",
                anchor="## Section",
            ),
        )
    )

    result = DefaultValidationEngine().validate(package, tmp_path)

    assert result.accepted is True
    assert result.findings[0].passed is True


def test_a_single_failing_item_rejects_the_whole_package(tmp_path):

    target = tmp_path / "doc.md"
    target.write_text(
        "# Title\n\n## Section\n\nBody.\n",
        encoding="utf-8",
    )

    package = _package(
        (
            PackageItem(
                target_path="doc.md",
                content="New paragraph.",
                rationale="test",
                anchor="## Section",
            ),
            PackageItem(
                target_path="missing.md",
                content="Other paragraph.",
                rationale="test",
            ),
        )
    )

    result = DefaultValidationEngine().validate(package, tmp_path)

    assert result.accepted is False
    assert result.findings[0].passed is True
    assert result.findings[1].passed is False
