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
    """
    Inside the perimeter, but not governed knowledge.
    """

    report = eligibility().evaluate(
        root=Path("/repo"),
        path=Path("/repo/docs/99-meta/NEXT-SESSION-TODO.md"),
    )

    assert not report.eligible
    assert report.reason == "excluded_path"


def test_a_path_outside_the_heritage_is_rejected():
    """
    The allow list runs first, and its refusal names a
    different thing: not "this was carved out" but "this was
    never in".

    A deny list makes every new directory governed knowledge by
    default. That is how a 0-byte README, a book manuscript and
    a package README came to be projected as Knowledge
    Artifacts.
    """

    for path in (
        "/repo/src/aistack/transport/README.md",
        "/repo/literature/la-politique-de-lautruche/README.md",
        "/repo/examples/README.md",
        "/repo/context/bundles/test.md",
    ):
        report = eligibility().evaluate(
            root=Path("/repo"),
            path=Path(path),
        )

        assert not report.eligible
        assert report.reason == "outside_governed_heritage"


def test_the_root_readme_is_the_entry_point():
    """
    The one file outside docs/ that stays: an agent boots from
    it.
    """

    report = eligibility().evaluate(
        root=Path("/repo"),
        path=Path("/repo/README.md"),
    )

    assert report.eligible


def test_a_prefix_is_a_path_boundary():
    """
    Plain startswith would make `docs` swallow `docsets/` and
    `inbox` swallow `inboxes/`.
    """

    report = eligibility().evaluate(
        root=Path("/repo"),
        path=Path("/repo/docsets/x.md"),
    )

    assert not report.eligible
    assert report.reason == "outside_governed_heritage"
