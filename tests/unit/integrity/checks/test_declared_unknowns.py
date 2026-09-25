from datetime import datetime

from aistack.contracts.artifact import KnowledgeArtifact
from aistack.contracts.context_bundle import ContextBundle
from aistack.contracts.integrity_finding import IntegritySeverity
from aistack.integrity.checks.declared_unknowns import (
    DeclaredUnknownCheck,
    declared_unknowns,
)


NOW = datetime(2026, 9, 25, 12, 0, 0)


def artifact(body: str, source: str = "docs/X.md") -> KnowledgeArtifact:
    return KnowledgeArtifact(
        id="X",
        title="T",
        declared_type="t",
        domain="Foundation",
        semantic_type="Knowledge Artifact",
        criticality="C2",
        owner="o",
        source=source,
        content=body,
        created_at=NOW,
        updated_at=NOW,
    )


def evaluate(*bodies: str):
    return DeclaredUnknownCheck().evaluate(
        ContextBundle(
            id="b",
            title="T",
            generated_at=NOW,
            source_commit="abc1234",
            artifacts=[
                artifact(body, f"docs/{i}.md")
                for i, body in enumerate(bodies)
            ],
        )
    )


# --------------------------------------------------------------------
# What the pattern catches
# --------------------------------------------------------------------


def test_not_verified_is_found():

    content = "The 2.4 canonical set is not verified against a real run.\n"

    assert declared_unknowns(content) == [
        (1, "The 2.4 canonical set is not verified against a real run.")
    ]


def test_grounding_unknown_is_found():

    content = "Confidence recorded as `grounding: unknown` for this claim.\n"

    assert len(declared_unknowns(content)) == 1


def test_recorded_as_lost_is_found():

    content = "The original decision was recorded as lost in GOV-0002.\n"

    assert len(declared_unknowns(content)) == 1


def test_does_not_decide_is_found():

    content = "FDN-0010 does not decide the overlap with FDN-0012.\n"

    assert len(declared_unknowns(content)) == 1


def test_keeps_no_definition_is_found():

    content = "The Glossary keeps no definition of the retired term.\n"

    assert len(declared_unknowns(content)) == 1


def test_an_open_points_heading_is_found():

    content = "## Open Points\n\nSomething undecided follows.\n"

    assert declared_unknowns(content) == [(1, "## Open Points")]


def test_a_singular_open_point_heading_is_found():

    content = "### Open Point\n"

    assert declared_unknowns(content) == [(1, "### Open Point")]


def test_the_line_number_and_the_text_are_reported():

    content = "First line.\nSecond line.\nThis is not verified yet.\n"

    assert declared_unknowns(content) == [
        (3, "This is not verified yet.")
    ]


def test_several_markers_on_different_lines_are_all_found():

    content = (
        "This is not verified.\n"
        "FDN-0010 does not decide the overlap.\n"
    )

    assert len(declared_unknowns(content)) == 2


def test_the_finding_is_an_observation():
    """
    Whether a declared unknown is still open, or has since been
    resolved by a `GOV-0002` entry elsewhere in the heritage, is a
    reading — exactly the comparison `STD-0300` § 8 excludes from a
    criterion. A `WARNING` would make `clean: False` on a condition
    already qualified, the same reasoning `claude-note-references`
    and `undated-assertions` already apply.
    """

    findings = evaluate("This claim is not verified.\n")

    assert findings[0].severity is IntegritySeverity.OBSERVATION
    assert findings[0].unit == "lines"


def test_lines_from_several_artifacts_are_all_named():

    findings = evaluate(
        "This is not verified.\n",
        "FDN-0010 does not decide the overlap.\n",
    )

    assert findings[0].affected == 2
    assert findings[0].subjects == (
        "docs/0.md:1 — This is not verified.",
        "docs/1.md:1 — FDN-0010 does not decide the overlap.",
    )


# --------------------------------------------------------------------
# What the pattern deliberately does not catch
# --------------------------------------------------------------------


def test_a_heritage_with_no_marker_is_not_reported():

    assert evaluate("Ordinary prose, nothing left open here.\n") == []


def test_a_backtick_quoted_marker_is_not_a_declaration():
    """
    This check's own docstring, and `STD-0300`'s explanatory prose,
    both name these markers in backticks or italics when describing
    the vocabulary rather than using it. The same `is_quoted` parity
    check `undated_assertions` and `claude_note_references` already
    apply.
    """

    content = "The markers include `not verified` and `does not decide`.\n"

    assert declared_unknowns(content) == []


def test_an_italicised_marker_is_not_a_declaration():

    content = "Named *not verified* in the criterion's original wording.\n"

    assert declared_unknowns(content) == []


def test_a_block_quotation_is_not_a_declaration():

    content = "> this is not verified\n"

    assert declared_unknowns(content) == []


def test_open_point_inside_a_sentence_is_not_a_heading():
    """
    `undated_assertions` and `claude_note_references` already show
    that a marker also occurs in prose *about* the pattern, which is
    not itself an instance of it. The heading regex only matches a
    line that is nothing but the heading.
    """

    content = "The section below is not an Open Points heading itself.\n"

    assert declared_unknowns(content) == []


def test_a_heritage_that_declares_nothing_is_not_reported():

    assert evaluate("Ordinary prose, no declared unknown at all.\n") == []
