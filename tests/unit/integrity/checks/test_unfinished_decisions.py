from datetime import datetime

from aistack.contracts.artifact import KnowledgeArtifact
from aistack.contracts.context_bundle import ContextBundle
from aistack.contracts.integrity_finding import IntegritySeverity
from aistack.integrity.checks.unfinished_decisions import (
    UnfinishedDecisionCheck,
    declares_implementation,
    implementation_rows,
    is_terminal,
)


NOW = datetime(2026, 8, 27, 12, 0, 0)


def decision(
    identifier: str,
    body: str,
    status: str = "Accepted",
    declared_type: str = "ADR",
) -> KnowledgeArtifact:

    return KnowledgeArtifact(
        id=identifier,
        title="a decision",
        declared_type=declared_type,
        domain="Architecture",
        semantic_type="ADR",
        criticality="C2",
        owner="Architecture",
        source=f"docs/01-architecture/adr/{identifier}.md",
        status=status,
        content=body,
        created_at=NOW,
        updated_at=NOW,
    )


def bundle(*artifacts: KnowledgeArtifact) -> ContextBundle:
    return ContextBundle(
        id="test-bundle",
        title="Test Bundle",
        generated_at=NOW,
        source_commit="0000000",
        artifacts=list(artifacts),
    )


TABLE = """# ADR-0000 — a decision

## Implementation state

| Step | State |
|---|---|
| Contracts | done — 2026-08-22 |
| Web surface | **abandoned — 2026-08-27** — see § 6 |
{extra}

## Consequences

Something else.
"""


def with_rows(*rows: str) -> str:
    return TABLE.format(extra="\n".join(rows))


# --------------------------------------------------------------------
# What discharges a row
# --------------------------------------------------------------------


def test_a_row_in_a_terminal_state_is_not_reported():

    check = UnfinishedDecisionCheck()

    assert check.evaluate(bundle(decision("ADR-0000", with_rows()))) == []


def test_a_row_in_no_terminal_state_is_reported():

    findings = UnfinishedDecisionCheck().evaluate(
        bundle(
            decision(
                "ADR-0000",
                with_rows("| Migration | not started |"),
            )
        )
    )

    assert len(findings) == 1
    assert findings[0].severity is IntegritySeverity.OBSERVATION
    assert findings[0].subjects == ("ADR-0000 — Migration → not started",)


def test_emphasis_does_not_hide_a_terminal_state():
    """
    ADR-0009's abandoned row is written `**abandoned — …**`, and a
    comparison against the raw cell would report it forever. The
    inverse matters more: emphasis must not *create* a terminal
    state either, which is why the strip happens before the
    prefix test and not after a substring search.
    """

    assert is_terminal("**done — 2026-08-22**")
    assert is_terminal("`abandoned`")
    assert not is_terminal("**not done**")
    assert not is_terminal("nearly done")


def test_a_sentence_is_not_a_state():
    """
    The row that produced this check read *not built, and not a
    blocker*. It is a sentence, it is not terminal, and it sat in
    an accepted decision for five days.
    """

    assert not is_terminal("**not built, and not a blocker** — see below")


# --------------------------------------------------------------------
# What is in scope
# --------------------------------------------------------------------


def test_a_proposed_decision_is_not_in_scope():
    """
    A proposed decision is allowed to be unimplemented — that is
    what proposing means. Only acceptance turns an unfinished row
    into an open state of the system.
    """

    findings = UnfinishedDecisionCheck().evaluate(
        bundle(
            decision(
                "ADR-0000",
                with_rows("| Migration | not started |"),
                status="Proposed",
            )
        )
    )

    assert findings == []


def test_a_table_in_an_artifact_that_is_not_a_decision_is_not_read():

    findings = UnfinishedDecisionCheck().evaluate(
        bundle(
            decision(
                "STD-0000",
                with_rows("| Migration | not started |"),
                declared_type="Standard",
            )
        )
    )

    assert findings == []


# --------------------------------------------------------------------
# Reading the table
# --------------------------------------------------------------------


def test_only_the_first_table_of_the_section_is_read():
    """
    **The reason this check has a stopping rule.** ADR-0009 carries
    a second table inside `## Implementation state`, under a `###`
    heading, whose cells are commands rather than states:

        | request a global diagnostic | `python3 -m aistack.cli.…` |

    A parser collecting every row of the section would read that
    command as a step in a non-terminal state and report it on
    every run, forever, with no way to make it stop.
    """

    body = (
        "## Implementation state\n\n"
        "| Step | State |\n|---|---|\n"
        "| Contracts | done — 2026-08-22 |\n\n"
        "### What the retirement delivered\n\n"
        "| Interaction | Replacement |\n|---|---|\n"
        "| a global diagnostic | `runtime_diagnose` |\n"
    )

    assert implementation_rows(body) == [
        ("Contracts", "done — 2026-08-22")
    ]


def test_the_section_ends_at_the_next_heading_of_its_own_level():

    body = (
        "## Implementation state\n\n"
        "| Step | State |\n|---|---|\n"
        "| Contracts | done — 2026-08-22 |\n\n"
        "## Consequences\n\n"
        "| Thing | State |\n|---|---|\n"
        "| Another | not started |\n"
    )

    assert implementation_rows(body) == [
        ("Contracts", "done — 2026-08-22")
    ]


def test_a_header_row_is_not_a_step():
    """
    The header is whatever precedes the separator. Counting it
    would report `Step → State` as an unfinished row of every
    decision that carries a table.
    """

    rows = implementation_rows(
        "## Implementation state\n\n"
        "| Step | State |\n|---|---|\n"
        "| Contracts | done — 2026-08-22 |\n"
    )

    assert ("Step", "State") not in rows
    assert len(rows) == 1


def test_a_decision_with_no_implementation_section_reads_no_rows():
    """
    Six of the nine accepted ADRs were in this case, measured
    2026-08-27, and STD-0100 v2.6 made it a rule that day. Reading
    no rows is not an error and is not coverage either; the
    finding above is what says so out loud.
    """

    assert implementation_rows("# ADR-0000\n\n## Context\n\nSomething.\n") == []


# --------------------------------------------------------------------
# Against the real heritage
# --------------------------------------------------------------------


def test_the_real_table_is_read_and_not_merely_absent():
    """
    **The control, and it is the point of this file.**

    This check reports nothing on the current heritage, because
    every row of ADR-0009's table was brought to a terminal state
    on 2026-08-27. A silent check is indistinguishable from one
    that parses nothing at all — a table renamed, a separator
    style changed, a regex that stops matching, and the report
    goes on reading `clean: True` while the section it was written
    for is unread.

    So this asserts the rows are *found*, by name, and that they
    are terminal — rather than asserting the finding count is
    zero, which the broken version would also satisfy.
    """

    from pathlib import Path

    root = Path(__file__).parents[4]

    adr = (
        root
        / "docs"
        / "01-architecture"
        / "adr"
        / "ADR-0009-Runtime-Evidence-Qualification.md"
    ).read_text()

    rows = implementation_rows(adr)

    assert len(rows) >= 7

    steps = [step for step, _ in rows]

    assert any("Web surface" in step for step in steps)
    assert any("Retirement" in step for step in steps)

    assert all(is_terminal(state) for _, state in rows)


def test_the_first_implementation_section_is_the_one_read():
    """
    **Found by mutation**, and the first two attempts at this test
    did not catch it either — which is the argument for running
    the pass rather than reasoning about the code.

    Removing the `break` at a section heading left every test
    green, because the row-stopping `break` exits the whole scan
    at the blank line after the first table. The heading break is
    reachable only when the first `## Implementation state`
    section holds **no** table: without it the parser walks on and
    reads a later section's table instead.

    What it protects is that the answer is the first section's,
    including when that answer is *nothing*. A parser that fell
    through to a later section would be guessing which section the
    author meant.
    """

    body = (
        "## Implementation state\n\n"
        "Described in prose, with no table.\n\n"
        "## Context\n\nSomething.\n\n"
        "## Implementation state\n\n"
        "| Step | State |\n|---|---|\n"
        "| Migration | not started |\n"
    )

    assert implementation_rows(body) == []


# --------------------------------------------------------------------
# A decision that declares no implementation state at all
# --------------------------------------------------------------------


def test_an_accepted_decision_that_declares_nothing_is_reported():
    """
    **The larger half, and it was invisible until 2026-08-27.**
    Six of the nine accepted ADRs carried no implementation
    section, and a check reading only tables reported zero on
    them — which reads as coverage.

    An accepted decision silent about its implementation is not a
    decision that was implemented. STD-0100 v2.6 says it must
    declare one; this says which do not.
    """

    findings = UnfinishedDecisionCheck().evaluate(
        bundle(decision("ADR-0000", "# ADR-0000\n\n## Context\n\nSomething.\n"))
    )

    assert len(findings) == 1
    assert findings[0].severity is IntegritySeverity.OBSERVATION
    assert findings[0].subjects == (
        "ADR-0000 — no implementation state is declared",
    )


def test_a_section_with_no_readable_table_is_reported_differently():
    """
    ADR-0003 and ADR-0005 are in this case: the section exists and
    says what the state is, in prose. The two are distinguished
    because they are not the same omission — one author described
    the state and one never asked.
    """

    body = (
        "## Implementation state\n\n"
        "Observed on 2026-08-21: one strategy exists, four do not.\n\n"
        "## Consequences\n"
    )

    findings = UnfinishedDecisionCheck().evaluate(
        bundle(decision("ADR-0000", body))
    )

    assert findings[0].subjects == (
        "ADR-0000 — the section carries no readable table",
    )

    assert declares_implementation(body)


def test_a_proposed_decision_declaring_nothing_is_not_reported():
    """
    The scope rule holds for both findings. A proposal has no
    implementation to declare.
    """

    findings = UnfinishedDecisionCheck().evaluate(
        bundle(
            decision(
                "ADR-0000",
                "# ADR-0000\n\n## Context\n",
                status="Proposed",
            )
        )
    )

    assert findings == []


def test_the_two_findings_are_separate():
    """
    One decision missing its declaration and another holding an
    unfinished row are different conditions with different
    remedies, and a reader ranking them needs them apart.
    """

    findings = UnfinishedDecisionCheck().evaluate(
        bundle(
            decision("ADR-0000", "# ADR-0000\n\n## Context\n"),
            decision("ADR-0001", with_rows("| Migration | not started |")),
        )
    )

    assert len(findings) == 2

    summaries = " ".join(f.summary for f in findings)

    assert "declare no implementation state" in summaries
    assert "no terminal state" in summaries


def test_a_declared_and_complete_decision_is_reported_by_neither():

    assert UnfinishedDecisionCheck().evaluate(
        bundle(decision("ADR-0000", with_rows()))
    ) == []


# --------------------------------------------------------------------
# The severities are a decision, and it is watched
# --------------------------------------------------------------------


def test_the_two_findings_carry_the_severity_the_owner_decided():
    """
    **Decided 2026-08-27 by the owner, and asserted here so the
    decision is watched rather than remembered.**

    An accepted decision declaring *no* implementation state is a
    governance gap STD-0100 v2.6 forbids, and rises to `WARNING`
    once every accepted decision declares — in that same commit,
    not before, since `clean: False` would forbid publishing the
    fix under OPS-0002 § 1. Until then it is an `OBSERVATION`, and
    this test moves with it.

    A *row* in no terminal state stays `OBSERVATION` for good.
    STD-P-002 puts specification before implementation, so an
    unfinished row is the ordinary state of work; a row reading
    `unqualified` is FDN-0003 Article 12 working.

    **The split was decided on a consequence.** Raised together,
    one open row would hold the heritage at `clean: False`
    indefinitely and the cheapest escape would be to delete the
    row — while a table holding only `done` asserts a decision is
    fully implemented. A severity that punished honesty would have
    bought silence.
    """

    findings = UnfinishedDecisionCheck().evaluate(
        bundle(
            decision("ADR-0000", "# ADR-0000\n\n## Context\n"),
            decision("ADR-0001", with_rows("| Migration | not started |")),
        )
    )

    by_kind = {
        ("declare no implementation state" in f.summary): f
        for f in findings
    }

    assert by_kind[True].severity is IntegritySeverity.OBSERVATION
    assert by_kind[False].severity is IntegritySeverity.OBSERVATION
