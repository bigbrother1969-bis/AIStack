from datetime import datetime

from aistack.contracts.artifact import KnowledgeArtifact
from aistack.contracts.context_bundle import ContextBundle
from aistack.contracts.integrity_finding import IntegritySeverity
from aistack.integrity.checks.claude_note_references import (
    ClaudeNoteReferenceCheck,
    note_citations,
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
    return ClaudeNoteReferenceCheck().evaluate(
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


def test_a_backtick_quoted_note_path_is_found():

    content = "Decision #9 (`claude/PLAN-UI-SELECTION-2026-08-29.md`).\n"

    assert note_citations(content) == [
        (1, "Decision #9 (`claude/PLAN-UI-SELECTION-2026-08-29.md`).")
    ]


def test_the_line_number_and_the_text_are_reported():

    content = "First line.\nSecond line.\nNamed in `claude/SESSION-2026-08-29.md`.\n"

    assert note_citations(content) == [
        (3, "Named in `claude/SESSION-2026-08-29.md`.")
    ]


def test_several_citations_on_different_lines_are_all_found():

    content = (
        "One (`claude/PLAN-J2-ARCHITECTURE-HTML-2026-09-10.md`).\n"
        "Two (`claude/PLAN-J3-TIME-FOUNDATION-2026-09-10.md`).\n"
    )

    assert len(note_citations(content)) == 2


def test_the_finding_is_an_observation():
    """
    Whether a citation is the sole statement of what it names is a
    reading, not a measurement — STD-0300 § 8. A WARNING would make
    `clean: False` on a citation that already restates its fact in
    the surrounding prose, the ordinary case audited on 2026-09-25.
    """

    findings = evaluate("Named in `claude/SESSION-2026-08-29.md`.\n")

    assert findings[0].severity is IntegritySeverity.OBSERVATION
    assert findings[0].unit == "lines"


def test_lines_from_several_artifacts_are_all_named():

    findings = evaluate(
        "Named in `claude/SESSION-2026-08-29.md`.\n",
        "Cited from `claude/ROADMAP-SYNTHESIS-2026-09-03.md` § 4.\n",
    )

    assert findings[0].affected == 2
    assert findings[0].subjects == (
        "docs/0.md:1 — Named in `claude/SESSION-2026-08-29.md`.",
        "docs/1.md:1 — Cited from `claude/ROADMAP-SYNTHESIS-2026-09-03.md` § 4.",
    )


# --------------------------------------------------------------------
# What the pattern deliberately does not catch
# --------------------------------------------------------------------


def test_a_heritage_with_no_citation_is_not_reported():

    assert evaluate("Nothing under claude/ is named here.\n") == []


def test_the_bare_directory_name_is_not_a_citation():
    """
    GOV-0002 § Purpose itself says knowledge once "lived in AI
    session records under `claude/`" — the directory, not a note.
    The pattern requires a `.md` path so that sentence is not
    matched, the same way it names no artifact by exclusion.
    """

    assert note_citations(
        "Knowledge once lived in AI session records under `claude/`.\n"
    ) == []


def test_a_path_without_backticks_is_not_a_citation():
    """
    Every real occurrence audited on 2026-09-25 quotes the path in
    backticks. A bare mention in prose is not the shape STD-0100
    governs, and reading it as one would widen the pattern past what
    was measured.
    """

    assert note_citations("See claude/SESSION-2026-08-29.md for detail.\n") == []


def test_a_block_quotation_is_not_a_citation():
    """
    STD-0100 prints a retired, hypothetical example of the defect
    this pattern names as a block quotation. A check that reported
    its own worked example would be indistinguishable from one that
    found a real occurrence.
    """

    content = "> cited from `claude/PLAN-UI-SELECTION-2026-08-29.md`\n"

    assert note_citations(content) == []


def test_a_heritage_that_cites_nothing_is_not_reported():

    assert evaluate("Ordinary prose, no citation at all.\n") == []
