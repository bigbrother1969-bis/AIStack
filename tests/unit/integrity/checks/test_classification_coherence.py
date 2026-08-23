from datetime import datetime

from aistack.contracts.artifact import KnowledgeArtifact
from aistack.contracts.context_bundle import ContextBundle
from aistack.contracts.integrity_finding import IntegritySeverity
from aistack.contracts.undeclared import UNDECLARED
from aistack.integrity.checks.classification_coherence import (
    ClassificationCoherenceCheck,
    domains_by_type,
)


NOW = datetime(2026, 8, 23, 12, 0, 0)


def artifact(
    identifier: str,
    declared_type: str,
    domain: str,
    semantic_type: str = "Knowledge Artifact",
    criticality: str = "C2",
) -> KnowledgeArtifact:
    return KnowledgeArtifact(
        id=identifier,
        title=f"Title of {identifier}",
        declared_type=declared_type,
        domain=domain,
        semantic_type=semantic_type,
        criticality=criticality,
        owner="Foundation",
        source=f"docs/{identifier}.md",
        content=f"---\nartifact:\n  id: {identifier}\n---\n",
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


def evaluate(*artifacts: KnowledgeArtifact):
    return ClassificationCoherenceCheck().evaluate(bundle(*artifacts))


# --------------------------------------------------------------------
# What the rule says
# --------------------------------------------------------------------


def test_one_type_in_one_domain_is_not_reported():

    findings = evaluate(
        artifact("FDN-0003", "Foundation Document", "Foundation"),
        artifact("FDN-0009", "Foundation Document", "Foundation"),
    )

    assert findings == []


def test_one_type_in_two_domains_is_reported():
    """
    The control case, and the only one that makes this check
    speak. The heritage has no violation — measured 2026-08-23
    across 65 artifacts and 19 types — so without a case that
    produces a finding, a check that never speaks and a check
    that cannot speak would read identically.
    """

    findings = evaluate(
        artifact("ADR-0003", "Architecture Document", "Architecture"),
        artifact("STD-0100", "Architecture Document", "Standards"),
    )

    assert len(findings) == 1
    assert findings[0].affected == 1
    assert findings[0].unit == "types"


def test_the_finding_names_the_type_and_both_readings():
    """
    A reader must be able to go and decide without re-running
    anything: which type is ambiguous, which domains it received,
    and which artifact declared each.
    """

    findings = evaluate(
        artifact("ADR-0003", "Architecture Document", "Architecture"),
        artifact("STD-0100", "Architecture Document", "Standards"),
    )

    assert findings[0].subjects == (
        "Architecture Document → Architecture (ADR-0003) · "
        "Standards (STD-0100)",
    )


def test_every_declaring_artifact_is_named_not_only_the_first():
    """
    Declared here in discovery order, which is not alphabetical
    order, so a finding that merely echoed the walk would read
    differently. Two projections of the same heritage must say
    the same sentence whatever order the tree was walked in.
    """

    findings = evaluate(
        artifact("STD-0100", "Architecture Document", "Standards"),
        artifact("ADR-0005", "Architecture Document", "Architecture"),
        artifact("ADR-0003", "Architecture Document", "Architecture"),
    )

    assert findings[0].subjects == (
        "Architecture Document → Architecture (ADR-0003, ADR-0005) · "
        "Standards (STD-0100)",
    )


def test_two_ambiguous_types_are_two_subjects_of_one_finding():
    """
    `Standard` is declared before `Register` here and reported
    after it: the finding is ordered by what it says, not by the
    order discovery happened to walk. Found by mutation —
    dropping the sort left the whole suite green.
    """

    findings = evaluate(
        artifact("A-1", "Standard", "Standards"),
        artifact("A-2", "Standard", "Foundation"),
        artifact("B-1", "Register", "Governance"),
        artifact("B-2", "Register", "Operations"),
    )

    assert len(findings) == 1
    assert findings[0].affected == 2
    assert findings[0].subjects == (
        "Register → Governance (B-1) · Operations (B-2)",
        "Standard → Foundation (A-2) · Standards (A-1)",
    )


def test_the_finding_is_a_warning():
    """
    Unlike a dangling reference, which can legitimately precede
    the document it cites, no state of the work has one type
    belonging to two domains. `clean: False` is the right answer,
    so the severity is not OBSERVATION.
    """

    findings = evaluate(
        artifact("A-1", "Standard", "Standards"),
        artifact("A-2", "Standard", "Foundation"),
    )

    assert findings[0].severity is IntegritySeverity.WARNING


def test_the_total_counts_types_not_artifacts():
    """
    `unit` is `types`, so `affected/total` must be read on the
    same scale. Printing `1/12 artifacts` for one ambiguous type
    among three would state something false, which is the defect
    `unit` was added for on 2026-08-22.
    """

    findings = evaluate(
        artifact("A-1", "Standard", "Standards"),
        artifact("A-2", "Standard", "Foundation"),
        artifact("B-1", "ADR", "Architecture"),
        artifact("C-1", "Register", "Governance"),
    )

    assert findings[0].total == 3


# --------------------------------------------------------------------
# The boundary STD-0100 draws, and two artifacts that depend on it
# --------------------------------------------------------------------


def test_one_type_with_two_semantic_types_is_not_reported():
    """
    `FDN-0011` is a `Foundation Document` whose `semantic_type`
    is `Principle`, where the eight others are
    `Knowledge Artifact`. STD-0100 states the rule holds on
    `domain` and on no other axis; a check completed to three
    axes would report this real artifact as a defect.
    """

    findings = evaluate(
        artifact(
            "FDN-0003",
            "Foundation Document",
            "Foundation",
            semantic_type="Knowledge Artifact",
        ),
        artifact(
            "FDN-0011",
            "Foundation Document",
            "Foundation",
            semantic_type="Principle",
        ),
    )

    assert findings == []


def test_one_type_with_two_criticalities_is_not_reported():
    """
    `ARCH-0009` is an `Architecture Document` at `C1` where the
    thirteen others are `C2`. Criticality is a judgement about
    importance, not a consequence of document kind.
    """

    findings = evaluate(
        artifact(
            "ADR-0003",
            "Architecture Document",
            "Architecture",
            criticality="C2",
        ),
        artifact(
            "ARCH-0009",
            "Architecture Document",
            "Architecture",
            criticality="C1",
        ),
    )

    assert findings == []


def test_two_types_sharing_one_domain_is_not_reported():
    """
    The rule runs one way. `Foundation Document` and
    `Foundation Principle` both sit in `Foundation`, and eleven
    of the 19 measured types share a domain with another.
    Reading the rule as a bijection would accuse most of the
    heritage.
    """

    findings = evaluate(
        artifact("FDN-0003", "Foundation Document", "Foundation"),
        artifact("FDN-P", "Foundation Principle", "Foundation"),
    )

    assert findings == []


# --------------------------------------------------------------------
# What is missing is not what is incoherent
# --------------------------------------------------------------------


def test_an_artifact_declaring_no_type_is_not_counted():
    """
    An absent qualification is reported by
    `classification-declaration`. Counting it here would make one
    gap speak twice, and would name it a *coherence* violation
    when nothing incoherent was said.
    """

    observed = domains_by_type(
        bundle(
            artifact("A-1", UNDECLARED, "Standards"),
            artifact("A-2", "Standard", "Standards"),
        )
    )

    assert set(observed) == {"Standard"}


def test_an_artifact_declaring_no_domain_is_not_counted():
    """
    Without this, every type holding one qualified artifact and
    one unqualified one would be reported as mapping to two
    domains — `Standards` and `unknown` — and the check would
    fire on a heritage that is merely incomplete.
    """

    findings = evaluate(
        artifact("A-1", "Standard", "Standards"),
        artifact("A-2", "Standard", UNDECLARED),
    )

    assert findings == []


def test_an_artifact_without_an_identifier_is_named_by_its_source():

    findings = evaluate(
        artifact("A-1", "Standard", "Standards"),
        KnowledgeArtifact(
            id=UNDECLARED,
            title="T",
            declared_type="Standard",
            domain="Foundation",
            semantic_type="Knowledge Artifact",
            criticality="C2",
            owner="o",
            source="docs/orphan.md",
            content="# Body\n",
            created_at=NOW,
            updated_at=NOW,
        ),
    )

    assert "docs/orphan.md" in findings[0].subjects[0]


def test_an_empty_bundle_produces_nothing():

    assert ClassificationCoherenceCheck().evaluate(bundle()) == []
