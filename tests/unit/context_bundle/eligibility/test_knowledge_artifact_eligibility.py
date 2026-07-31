from pathlib import Path

from aistack.context_bundle.eligibility import (
    KnowledgeArtifactEligibility,
)


def eligibility() -> KnowledgeArtifactEligibility:
    return KnowledgeArtifactEligibility()


def test_accept_markdown():

    assert eligibility().is_eligible(
        root=Path("."),
        path=Path("docs/foo.md"),
    )


def test_reject_extension():

    assert not eligibility().is_eligible(
        root=Path("."),
        path=Path("docs/foo.txt"),
    )


def test_reject_git():

    assert not eligibility().is_eligible(
        root=Path("."),
        path=Path(".git/config.md"),
    )


def test_reject_pycache():

    assert not eligibility().is_eligible(
        root=Path("."),
        path=Path("__pycache__/foo.md"),
    )


def test_reject_generated_bundle():

    assert not eligibility().is_eligible(
        root=Path("."),
        path=Path("context/bundles/bundle.md"),
    )
