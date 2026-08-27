from datetime import datetime

import pytest

from aistack.contracts.artifact import KnowledgeArtifact
from aistack.contracts.context_bundle import ContextBundle
from aistack.contracts.integrity_finding import IntegritySeverity
from aistack.integrity.checks.undated_assertions import (
    UndatedAssertionCheck,
    is_quoted,
    undated_lines,
)


NOW = datetime(2026, 8, 27, 12, 0, 0)


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
    return UndatedAssertionCheck().evaluate(
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
# What the rule catches
# --------------------------------------------------------------------


@pytest.mark.parametrize(
    "marker",
    ["today", "currently", "not yet", "for now"],
)
def test_each_governed_marker_is_found(marker):

    found = undated_lines(f"The validator does {marker} observe it.\n")

    assert len(found) == 1


def test_the_line_number_and_the_text_are_reported():
    """
    A reader must be able to go straight there. The check does not
    know which sentence is stale, so the least it owes is the
    place.
    """

    content = "First line.\nSecond line.\nIt exists in this heritage today.\n"

    assert undated_lines(content) == [
        (3, "It exists in this heritage today.")
    ]


def test_a_dated_assertion_is_not_reported():
    """
    The rule discharged. STD-0100 asks for a date and a commit;
    a line carrying either has said when it was true.
    """

    assert undated_lines(
        "As of 2026-08-20 the validator does not observe it.\n"
    ) == []

    assert undated_lines(
        "The validator does not observe it today, `085fe3b`.\n"
    ) == []


def test_the_finding_is_an_observation():
    """
    Whether a sentence carrying a marker has gone stale is not
    derivable — OS-017 says so in its own text. What is derivable
    is where to look.

    A WARNING would make `clean: False` on prose that is perfectly
    correct, and the report would be obeyed by deletion rather
    than read.
    """

    findings = evaluate("It exists in this heritage today.\n")

    assert findings[0].severity is IntegritySeverity.OBSERVATION
    assert findings[0].unit == "lines"


def test_lines_from_several_artifacts_are_all_named():

    findings = evaluate(
        "It exists in this heritage today.\n",
        "AIStack currently distinguishes two Profile types.\n",
    )

    assert findings[0].affected == 2
    assert findings[0].subjects == (
        "docs/0.md:1 — It exists in this heritage today.",
        "docs/1.md:1 — AIStack currently distinguishes two Profile types.",
    )


def test_a_heritage_that_dates_everything_is_not_reported():

    assert evaluate("As of 2026-08-27 it exists.\n") == []


# --------------------------------------------------------------------
# A quotation is not an assertion
# --------------------------------------------------------------------


def test_a_marker_inside_emphasis_is_a_quotation():
    """
    STD-0100 lists the markers it forbids, in emphasis. A check
    that read that list as a defect would report the standard for
    teaching its own rule — and the register quotes the same list
    when describing OS-017.

    That is why no artifact is excluded by name. Excluding a file
    for being noisy would be the check adapting to the data
    instead of to the rule.
    """

    content = (
        "The words that hide a date: *today*, *currently*, "
        "*not yet*, *for now*.\n"
    )

    assert undated_lines(content) == []


def test_a_marker_inside_backticks_is_a_quotation():

    assert undated_lines("The marker `today` is one of them.\n") == []


def test_a_block_quotation_is_not_an_assertion():
    """
    STD-0100 prints the defect it forbids as a worked example:

        > ✗ the validator does not observe `version` today
    """

    content = "> the validator does not observe it today\n"

    assert undated_lines(content) == []


def test_a_marker_after_a_closed_quotation_is_an_assertion():
    """
    The parity test must not swallow the whole line once a
    quotation has opened and closed. `*deliberate*` is emphasis
    that ends, and what follows it is the artifact speaking.
    """

    content = "The practice is *deliberate*, and nothing states it today.\n"

    assert len(undated_lines(content)) == 1


def test_the_quotation_test_reads_only_what_precedes_the_marker():

    assert is_quoted("plain text today, then *emphasis*", 11) is False
    assert is_quoted('he wrote "not yet" there', 10) is True


# --------------------------------------------------------------------
# What the rule deliberately does not catch
# --------------------------------------------------------------------


@pytest.mark.parametrize("word", ["still", "remains"])
def test_the_two_removed_markers_are_not_reported(word):
    """
    STD-0100 listed six markers until 2026-08-27. Two were
    measured and removed: `remains` alone accounted for 50 of 113
    occurrences and carried a date in one of them, because it
    overwhelmingly introduces timeless statements — *the
    repository remains the authoritative source of governed
    knowledge* hides no date at all.

    Keeping them would have published over a hundred lines, and a
    report nobody can read is not a report. The standard was
    corrected by the measurement rather than the check narrowed
    against the standard.
    """

    assert undated_lines(f"The repository {word} the source.\n") == []
