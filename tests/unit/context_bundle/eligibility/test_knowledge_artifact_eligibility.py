from pathlib import Path

from aistack.context_bundle.eligibility import (
    KnowledgeArtifactEligibility,
)


def eligibility():
    return KnowledgeArtifactEligibility()


def test_markdown_is_eligible():

    report = eligibility().evaluate(
        root=Path("/repo"),
        path=Path("/repo/docs/test.md"),
    )

    assert report.eligible
    assert report.reason == "knowledge_artifact"


def test_non_markdown_is_rejected():

    report = eligibility().evaluate(
        root=Path("/repo"),
        path=Path("/repo/docs/test.txt"),
    )

    assert not report.eligible
    assert report.reason == "unsupported_extension"


def test_git_directory_is_rejected():

    report = eligibility().evaluate(
        root=Path("/repo"),
        path=Path("/repo/.git/test.md"),
    )

    assert not report.eligible
    assert report.reason == "excluded_directory"


def test_archive_directory_is_rejected():

    report = eligibility().evaluate(
        root=Path("/repo"),
        path=Path("/repo/archive/test.md"),
    )

    assert not report.eligible
    assert report.reason == "excluded_directory"


def test_excluded_path_is_rejected():

    report = eligibility().evaluate(
        root=Path("/repo"),
        path=Path("/repo/context/bundles/test.md"),
    )

    assert not report.eligible
    assert report.reason == "excluded_path"
