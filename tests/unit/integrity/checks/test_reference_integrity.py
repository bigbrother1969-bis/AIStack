from datetime import datetime

from aistack.contracts.artifact import KnowledgeArtifact
from aistack.contracts.context_bundle import ContextBundle
from aistack.contracts.integrity_finding import IntegritySeverity
from aistack.integrity.checks.reference_integrity import (
    ReferenceIntegrityCheck,
    declared_identifier,
    declared_references,
)


NOW = datetime(2026, 8, 23, 12, 0, 0)


def document(identifier: str, references: list[str] | None = None) -> str:
    block = f"---\nartifact:\n  id: {identifier}\n  title: T\n"

    if references is not None:
        block += "\nrelations:\n  references:\n"
        block += "".join(f"    - {r}\n" for r in references)

    return block + "---\n\n# Body\n"


def artifact(content: str, source: str = "x.md") -> KnowledgeArtifact:
    """
    Built with a hash for `id`, exactly as the pipeline does.

    That is the point of the fixture: `KnowledgeArtifact.id` is
    the content hash, not the governed identifier (OS-021), and a
    test that passed the identifier here would prove the check
    works on data the projection never contains.
    """

    return KnowledgeArtifact(
        id="0" * 64,
        title="T",
        declared_type="t",
        domain="Foundation",
        semantic_type="Principle",
        criticality="C2",
        owner="o",
        source=source,
        content=content,
        created_at=NOW,
        updated_at=NOW,
    )


def bundle(*contents: str) -> ContextBundle:
    return ContextBundle(
        id="b",
        title="T",
        generated_at=NOW,
        source_commit="abc1234",
        artifacts=[artifact(c, f"{i}.md") for i, c in enumerate(contents)],
    )


# --------------------------------------------------------------------
# Reading the frontmatter, which is where identity survives
# --------------------------------------------------------------------


def test_the_declared_identifier_is_read_not_the_hash():

    assert declared_identifier(document("FDN-0003")) == "FDN-0003"


def test_an_artifact_without_frontmatter_declares_no_identifier():

    assert declared_identifier("# Just a heading\n") is None


def test_references_are_read_from_the_frontmatter():

    content = document("STD-0300", ["FDN-0003", "FDN-0012"])

    assert declared_references(content) == ["FDN-0003", "FDN-0012"]


def test_an_artifact_declaring_no_relations_references_nothing():

    assert declared_references(document("FDN-0003")) == []


def test_an_unterminated_frontmatter_is_unreadable_not_empty():
    """
    "Nobody could read it" and "it references nothing" are
    different facts, and the check reports them separately.
    """

    assert declared_references("---\nartifact:\n  id: X\n") is None


def test_invalid_yaml_is_unreadable_not_empty():

    assert declared_references("---\nartifact: [unclosed\n---\n") is None


def test_references_that_are_not_a_list_are_unreadable():
    """
    `references: FDN-0003` instead of a list. Iterating a string
    would yield eight single characters and report eight dangling
    references named `F`, `D`, `N` — a report that is precise,
    confident and entirely wrong.
    """

    content = (
        "---\nartifact:\n  id: X\n\n"
        "relations:\n  references: FDN-0003\n---\n"
    )

    assert declared_references(content) is None


# --------------------------------------------------------------------
# What the check publishes
# --------------------------------------------------------------------


def test_a_reference_to_a_declared_artifact_is_not_reported():

    findings = ReferenceIntegrityCheck().evaluate(
        bundle(
            document("FDN-0003"),
            document("STD-0300", ["FDN-0003"]),
        )
    )

    assert findings == []


def test_a_reference_to_nothing_is_reported_with_both_ends():
    """
    The control case. This check publishes nothing on the current
    heritage, so without a case that makes it speak it would be
    indistinguishable from a check that never speaks.

    The real occurrence it was written for: five artifacts
    declared `- PRINCIPLES-REGISTRY` while the registry's
    identifier was `FDN-PRINCIPLES`.
    """

    findings = ReferenceIntegrityCheck().evaluate(
        bundle(
            document("FDN-0012"),
            document("FDN-0009", ["PRINCIPLES-REGISTRY"]),
        )
    )

    assert len(findings) == 1
    assert findings[0].affected == 1
    assert findings[0].subjects == ("FDN-0009 → PRINCIPLES-REGISTRY",)
    assert findings[0].unit == "references"


def test_the_finding_is_an_observation():
    """
    The owner's choice, 2026-08-23. A WARNING would make
    `clean: False` and fail STD-0300 criterion 2.6 until every
    reference resolves — which would also forbid committing an
    artifact that cites a document being written.
    """

    findings = ReferenceIntegrityCheck().evaluate(
        bundle(document("FDN-0009", ["NOPE"]))
    )

    assert findings[0].severity is IntegritySeverity.OBSERVATION


def test_several_dangling_references_are_all_named():

    findings = ReferenceIntegrityCheck().evaluate(
        bundle(
            document("FDN-0009", ["A", "B"]),
            document("FDN-0010", ["A"]),
        )
    )

    assert findings[0].affected == 3
    assert set(findings[0].subjects) == {
        "FDN-0009 → A",
        "FDN-0009 → B",
        "FDN-0010 → A",
    }


def test_an_unreadable_artifact_is_reported_separately():
    """
    Reporting both as one number would let "no broken
    references" and "nobody could tell" read identically.
    """

    findings = ReferenceIntegrityCheck().evaluate(
        bundle("---\nartifact: [unclosed\n---\n")
    )

    assert len(findings) == 1
    assert "unverified, not absent" in findings[0].summary
    assert findings[0].unit == "artifacts"


def test_an_unreadable_artifact_is_named_by_its_source():
    """
    An artifact whose frontmatter will not parse has no readable
    identifier either, so it is named by the file it came from —
    which is what a reader needs to go and fix it.
    """

    findings = ReferenceIntegrityCheck().evaluate(
        ContextBundle(
            id="b",
            title="T",
            generated_at=NOW,
            source_commit="abc1234",
            artifacts=[
                artifact("---\nbroken: [\n---\n", source="docs/x.md")
            ],
        )
    )

    assert findings[0].subjects == ("docs/x.md",)


def test_the_two_kinds_are_reported_as_two_findings():

    findings = ReferenceIntegrityCheck().evaluate(
        bundle(
            document("FDN-0009", ["NOPE"]),
            "---\nartifact: [unclosed\n---\n",
        )
    )

    assert len(findings) == 2
    assert {f.unit for f in findings} == {"references", "artifacts"}


def test_the_current_heritage_declares_no_dangling_reference():
    """
    The state of 2026-08-23, and the reason this check publishes
    nothing today. It was not always so: five references were
    dangling until the rename of `FDN-PRINCIPLES` earlier the
    same day.
    """

    from aistack.integrity.bundle_reader import read_bundle
    from pathlib import Path

    projection = (
        Path(__file__).parents[4]
        / "context"
        / "bundles"
        / "AIStack-Context-Bundle.zip"
    )

    if not projection.exists():
        return

    findings = ReferenceIntegrityCheck().evaluate(read_bundle(projection))

    assert findings == [], [f.subjects for f in findings]
