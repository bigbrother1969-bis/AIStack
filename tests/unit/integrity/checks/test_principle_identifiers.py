from datetime import datetime

from aistack.contracts.artifact import KnowledgeArtifact
from aistack.contracts.context_bundle import ContextBundle
from aistack.contracts.integrity_finding import IntegritySeverity
from aistack.integrity.checks.principle_identifiers import (
    PrincipleIdentifierCheck,
    cited_identifiers,
    registered_identifiers,
)


NOW = datetime(2026, 8, 23, 12, 0, 0)


def table(*rows: str) -> str:
    return (
        "| ID | Principle | Criticality |\n"
        "|----|-----------|-------------|\n"
        + "".join(f"| {row} | some principle | C2 |\n" for row in rows)
    )


def artifact(
    identifier: str,
    body: str,
    source: str | None = None,
) -> KnowledgeArtifact:
    return KnowledgeArtifact(
        id=identifier,
        title=f"Title of {identifier}",
        declared_type="t",
        domain="Foundation",
        semantic_type="Knowledge Artifact",
        criticality="C3",
        owner="Foundation",
        source=source or f"docs/{identifier}.md",
        content=body,
        created_at=NOW,
        updated_at=NOW,
    )


def bundle(*artifacts: KnowledgeArtifact) -> ContextBundle:
    return ContextBundle(
        id="b",
        title="T",
        generated_at=NOW,
        source_commit="abc1234",
        artifacts=list(artifacts),
    )


def registry(*rows: str) -> KnowledgeArtifact:
    return artifact("FDN-0012", table(*rows))


def evaluate(*artifacts: KnowledgeArtifact):
    return PrincipleIdentifierCheck().evaluate(bundle(*artifacts))


# --------------------------------------------------------------------
# Reading the registry, which is a table and not a file tree
# --------------------------------------------------------------------


def test_the_rows_of_the_principle_table_are_read():

    assert registered_identifiers(
        table("FDN-P-001", "FDN-P-002")
    ) == ["FDN-P-001", "FDN-P-002"]


def test_a_malformed_row_is_read_not_skipped():
    """
    The reason the reader is positional rather than pattern-based.
    Collecting only cells that *match* the governed form would
    find conforming identifiers only, and would report `FDN-006`
    as absent rather than as wrong — which is the exact failure
    OS-005 describes: writing it *would pass every check*.
    """

    assert registered_identifiers(table("FDN-006")) == ["FDN-006"]


def test_rows_outside_an_id_table_are_not_read():
    """
    FDN-0012 carries a `| principle | artifact |` table quoting
    the three-digit forms retired on 2026-08-21. Reading those as
    declarations would make the registry's account of its own
    history a violation of the rule that history established —
    four false positives on the real artifact.
    """

    content = (
        "| principle | artifact |\n"
        "|---|---|\n"
        "| `FDN-005` — a principle | `FDN-0005` — an artifact |\n"
        "\n"
        + table("FDN-P-005")
    )

    assert registered_identifiers(content) == ["FDN-P-005"]


def test_a_table_ends_where_the_rows_end():

    content = table("FDN-P-001") + "\nSome prose.\n\n| x | y |\n| a | b |\n"

    assert registered_identifiers(content) == ["FDN-P-001"]


def test_a_separator_row_is_not_an_identifier():

    assert registered_identifiers(table()) == []


# --------------------------------------------------------------------
# What the check publishes about registered identifiers
# --------------------------------------------------------------------


def test_a_conforming_registry_is_not_reported():

    assert evaluate(registry("FDN-P-001", "OPS-P-004")) == []


def test_the_three_digit_form_is_reported():
    """
    The case OS-005 names verbatim: *writing `FDN-006` in
    FDN-0012 tomorrow would pass every check*.
    """

    findings = evaluate(registry("FDN-P-001", "FDN-006"))

    assert len(findings) == 1
    assert findings[0].subjects == ("FDN-006",)
    assert findings[0].unit == "principles"


def test_an_artifact_form_in_the_registry_is_reported():
    """
    `FDN-0011` is Contract-Based Engineering, an artifact. A row
    of the registry carrying it would state that a document is a
    principle — the collision the `P` exists to prevent.
    """

    findings = evaluate(registry("FDN-0011"))

    assert findings[0].subjects == ("FDN-0011",)


def test_a_prefix_no_domain_uses_is_reported():
    """
    `KNW` for Knowledge Assets is not a governed prefix: no
    principle has been registered in that domain, so no prefix
    has been decided, and deciding one is the owner's (GOV-P-001).
    """

    findings = evaluate(registry("KNW-P-001"))

    assert findings[0].subjects == ("KNW-P-001",)


def test_the_wrong_number_of_digits_is_reported():

    findings = evaluate(registry("FDN-P-1", "FDN-P-0001"))

    assert findings[0].subjects == ("FDN-P-0001", "FDN-P-1")


def test_a_malformed_registered_identifier_is_a_warning():
    """
    The form is decided and the registry is one table. No state
    of the work has a principle registered under a name the
    standard forbids, so `clean: False` is the right answer.
    """

    findings = evaluate(registry("FDN-006"))

    assert findings[0].severity is IntegritySeverity.WARNING


def test_the_total_counts_registered_principles():

    findings = evaluate(registry("FDN-P-001", "FDN-P-002", "FDN-006"))

    assert findings[0].affected == 1
    assert findings[0].total == 3


# --------------------------------------------------------------------
# What the check publishes about citations
# --------------------------------------------------------------------


def test_a_citation_of_a_registered_principle_is_not_reported():

    findings = evaluate(
        registry("FDN-P-005"),
        artifact("STD-0100", "This follows FDN-P-005.\n"),
    )

    assert findings == []


def test_a_citation_the_registry_does_not_declare_is_reported():
    """
    The renumbering of 2026-08-21 missed the Operations family —
    four principles and one citation of `OPS-004` in STD-0300 —
    and the gap survived a day because nothing compared the two
    sets.
    """

    findings = evaluate(
        registry("FDN-P-005"),
        artifact("STD-0300", "Per OPS-P-004, observe first.\n"),
    )

    assert len(findings) == 1
    assert findings[0].subjects == ("OPS-P-004 ← docs/STD-0300.md",)


def test_the_citation_finding_names_every_artifact_that_wrote_it():

    findings = evaluate(
        registry("FDN-P-005"),
        artifact("A", "See ENG-P-009.\n", source="docs/b.md"),
        artifact("B", "See ENG-P-009.\n", source="docs/a.md"),
    )

    assert findings[0].subjects == (
        "ENG-P-009 ← docs/a.md, docs/b.md",
    )


def test_an_unregistered_citation_is_an_observation():
    """
    It was a WARNING for four hours on 2026-08-23, and it fired
    on the commit qualifying OS-005's own family: the register
    recorded a decision to create `FDN-P-015` and `ENG-P-007`
    before the rows existed, and `clean: False` forbade
    recording a decision before its consequence.

    Same asymmetry as `reference-integrity`. A heritage whose
    method is *decide, record, then execute* has to be able to
    commit the middle step. The occurrence OS-005 was opened for
    is still published at every projection, which is what would
    have caught it a day earlier.
    """

    findings = evaluate(
        registry("FDN-P-005"),
        artifact("STD-0300", "Per OPS-P-004, observe first.\n"),
    )

    assert findings[0].severity is IntegritySeverity.OBSERVATION


def test_the_two_kinds_are_reported_as_two_findings():
    """
    A malformed row and an unresolvable citation are different
    questions — one is a registry that names a principle wrongly,
    the other a heritage that invokes a principle nobody
    registered. Reporting them as one number would let them read
    identically, and they do not even carry the same severity.
    """

    findings = evaluate(
        registry("FDN-006"),
        artifact("STD-0100", "Per ARC-P-099.\n"),
    )

    assert len(findings) == 2
    assert [f.severity for f in findings] == [
        IntegritySeverity.WARNING,
        IntegritySeverity.OBSERVATION,
    ]


def test_a_malformed_row_declares_nothing_and_its_citations_are_reported():
    """
    Found by mutation: letting a malformed row count as a
    declaration left the whole suite green, and it would have
    hidden the more expensive half of the problem.

    A registry row naming a principle wrongly does not govern
    that name, so an artifact citing it cites nothing governed.
    The reader needs both ends — the row to fix, and every
    artifact that will have to be edited with it.
    """

    findings = evaluate(
        registry("FDN-P-0001"),
        artifact("STD-0100", "Per FDN-P-0001.\n"),
    )

    assert len(findings) == 2
    assert findings[0].subjects == ("FDN-P-0001",)
    assert findings[1].subjects == (
        "FDN-P-0001 ← docs/FDN-0012.md, docs/STD-0100.md",
    )


def test_a_citation_is_collected_with_its_source():

    citations = cited_identifiers(
        bundle(artifact("A", "GOV-P-001 and STD-P-004.\n"))
    )

    assert citations == {
        "GOV-P-001": ["docs/A.md"],
        "STD-P-004": ["docs/A.md"],
    }


# --------------------------------------------------------------------
# The absent registry, which is not a pass
# --------------------------------------------------------------------


def test_a_bundle_without_the_registry_is_reported():
    """
    A check that returned `[]` here would be green on a bundle in
    which nothing governs the principles and every citation
    designates nothing — the shape of the test that passed on a
    fresh clone while verifying nothing, found 2026-08-23.
    """

    findings = evaluate(artifact("STD-0100", "Per FDN-P-005.\n"))

    assert len(findings) == 1
    assert "unverified, not conforming" in findings[0].summary


def test_the_absent_registry_is_an_observation_not_a_warning():
    """
    A partial bundle carrying no registry is not a heritage that
    broke a rule; it is a projection nobody could ask the
    question of. Making it `clean: False` would fail STD-0300
    criterion 2.6 on every selective bundle.

    Whether *this* repository's projection must carry FDN-0012 is
    a different question with a different answer, and it is
    asserted over the real heritage in the integration suite.
    """

    findings = evaluate(artifact("STD-0100", "Per FDN-P-005.\n"))

    assert findings[0].severity is IntegritySeverity.OBSERVATION


def test_an_empty_bundle_is_reported_too():

    findings = PrincipleIdentifierCheck().evaluate(bundle())

    assert len(findings) == 1
    assert "absent" in findings[0].summary
