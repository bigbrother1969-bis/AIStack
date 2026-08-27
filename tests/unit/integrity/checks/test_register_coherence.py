from datetime import datetime

from aistack.contracts.artifact import KnowledgeArtifact
from aistack.contracts.context_bundle import ContextBundle
from aistack.contracts.integrity_finding import IntegritySeverity
from aistack.integrity.checks.register_coherence import (
    RegisterCoherenceCheck,
    read_entries,
)


NOW = datetime(2026, 8, 27, 12, 0, 0)


def entry(identifier: str, nature: str, state: str) -> str:
    return (
        f"#### GOV-0002/{identifier} — a one-line statement\n\n"
        f"**Nature** `{nature}` · **Opened** 2026-08-27 · "
        f"**State** {state}\n"
        f"**Observed** something\n"
        f"**Derivable** no\n"
        f"**Qualification** none required.\n\n"
    )


def register(*sections: tuple[str, list[str]]) -> KnowledgeArtifact:
    body = "# GOV-0002 — Open State Register\n\n"

    for heading, entries in sections:
        body += f"# {heading}\n\n" + "".join(entries) + "---\n\n"

    return KnowledgeArtifact(
        id="GOV-0002",
        title="Open State Register",
        declared_type="Governance Register",
        domain="Governance",
        semantic_type="Knowledge Artifact",
        criticality="C2",
        owner="Foundation",
        source="docs/03-governance/GOV-0002.md",
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


def evaluate(*sections: tuple[str, list[str]]):
    return RegisterCoherenceCheck().evaluate(bundle(register(*sections)))


# --------------------------------------------------------------------
# Reading the register, which is headings and not frontmatter
# --------------------------------------------------------------------


def test_an_entry_is_read_with_the_section_holding_it():

    entries = read_entries(
        register(
            ("Contract debt", [entry("OS-001", "contract-debt", "open")]),
            ("Resolved", [entry("OS-002", "contract-debt", "resolved")]),
        ).content
    )

    assert [(e.id, e.section, e.state) for e in entries] == [
        ("OS-001", "Contract debt", "open"),
        ("OS-002", "Resolved", "resolved"),
    ]


def test_the_template_entry_is_not_an_entry():
    """
    The register documents its own form under *How an entry is
    written*, using `OS-000` and the words `open | resolved`.
    Reading it as an entry would report the register's
    instructions as a defect of the register.
    """

    entries = read_entries(
        register(
            ("Contract debt", [entry("OS-000", "contract-debt", "open")])
        ).content
    )

    assert entries == []


def test_a_section_heading_ends_the_entry_above_it():
    """
    Found by mutation. An entry that declares no fields — because
    it is being written, or is malformed — must not adopt the
    first `**State**` that appears further down the file, which
    after a section heading belongs to another part of the
    register entirely.

    Without the guard this reports a *false* incoherence: the
    unfinished entry in one section is credited with a state read
    from prose in the next, and named as misplaced.
    """

    body = (
        "# GOV-0002 — Open State Register\n\n"
        "# Contract debt\n\n"
        "#### GOV-0002/OS-030 — being written\n\n"
        "# Resolved\n\n"
        "An entry moves here with its date, and reads\n"
        "**State** resolved once it has.\n\n"
    )

    entries = read_entries(body)

    assert [(e.id, e.section, e.state) for e in entries] == [
        ("OS-030", "Contract debt", None)
    ]

    artifact = register()
    artifact = KnowledgeArtifact(
        **{**artifact.__dict__, "content": body}
    )

    assert RegisterCoherenceCheck().evaluate(bundle(artifact)) == []


# --------------------------------------------------------------------
# A state and a section that disagree
# --------------------------------------------------------------------


def test_a_coherent_register_is_not_reported():

    findings = evaluate(
        ("Contract debt", [entry("OS-001", "contract-debt", "open")]),
        ("Resolved", [entry("OS-002", "contract-debt", "resolved")]),
    )

    assert findings == []


def test_an_open_entry_under_resolved_is_reported():
    """
    The occurrence, 2026-08-27: OS-029 was filed under *Resolved*
    while declaring `State open` — an entry announcing itself as
    open inside the section for closed ones. Found by a human
    reading the file.
    """

    findings = evaluate(
        ("Resolved", [entry("OS-029", "contract-debt", "open")]),
    )

    assert len(findings) == 1
    assert findings[0].subjects == (
        "OS-029 declares open and sits under Resolved",
    )
    assert findings[0].unit == "entries"


def test_a_resolved_entry_outside_resolved_is_reported():
    """
    The other direction, and it is the expensive one: a closed
    entry left among the open ones makes the heritage look worse
    than it is, and the register's whole thesis is that a resolved
    state is recorded rather than forgotten.
    """

    findings = evaluate(
        ("Contract debt", [entry("OS-002", "contract-debt", "resolved")]),
    )

    assert findings[0].subjects == (
        "OS-002 declares resolved and sits under Contract debt",
    )


def test_a_partial_state_is_not_a_resolved_one():
    """
    OS-012 declares `State partially mitigated`. It is not
    resolved, so it belongs among the open entries, and a check
    that treated any non-`open` word as closed would move it.
    """

    findings = evaluate(
        ("Risks", [entry("OS-012", "risk", "partially mitigated")]),
    )

    assert findings == []


def test_the_finding_is_a_warning():
    """
    A register whose two statements of one fact disagree is not a
    state of the work. It is the record of the work being wrong
    about itself, and this register is the primary record of
    conditions no artifact states about itself.
    """

    findings = evaluate(
        ("Resolved", [entry("OS-029", "contract-debt", "open")]),
    )

    assert findings[0].severity is IntegritySeverity.WARNING


# --------------------------------------------------------------------
# A section holding two natures
# --------------------------------------------------------------------


def test_a_section_of_one_nature_is_not_reported():

    findings = evaluate(
        (
            "Decisions",
            [
                entry("OS-013", "decision", "open"),
                entry("OS-014", "decision", "open"),
            ],
        ),
    )

    assert findings == []


def test_a_section_holding_two_natures_is_reported():
    """
    The occurrence, 2026-08-23: OS-023 and OS-024 were filed under
    *Defects* while declaring `non-conforming`, beside the two
    real defects of `sync_mirrors.sh`.

    This is deliberately not a check of nature against section
    *name*. That mapping lives in the register's prose, and a
    second copy in this module would be one more pair of
    projections to drift apart.
    """

    findings = evaluate(
        (
            "Defects",
            [
                entry("OS-009", "defect", "open"),
                entry("OS-023", "non-conforming", "open"),
            ],
        ),
    )

    assert len(findings) == 1
    assert findings[0].unit == "sections"
    assert findings[0].subjects == (
        "Defects → defect (OS-009) · non-conforming (OS-023)",
    )


def test_the_resolved_section_may_hold_every_nature():
    """
    It holds whatever has been closed, and closing does not sort
    by nature. Applying homogeneity there would report a register
    doing exactly what it promises.
    """

    findings = evaluate(
        (
            "Resolved",
            [
                entry("OS-002", "contract-debt", "resolved"),
                entry("OS-009", "defect", "resolved"),
                entry("OS-011", "published", "resolved"),
            ],
        ),
    )

    assert findings == []


def test_the_two_kinds_are_reported_as_two_findings():

    findings = evaluate(
        (
            "Defects",
            [
                entry("OS-009", "defect", "open"),
                entry("OS-023", "non-conforming", "open"),
            ],
        ),
        ("Resolved", [entry("OS-029", "contract-debt", "open")]),
    )

    assert len(findings) == 2
    assert {f.unit for f in findings} == {"entries", "sections"}


# --------------------------------------------------------------------
# The absent register
# --------------------------------------------------------------------


def test_a_bundle_without_the_register_is_observed_not_silent():
    """
    A partial bundle may legitimately carry no register, so this
    is an OBSERVATION — the same answer `principle-identifiers`
    gives to a projection without FDN-0012. Returning `[]` would
    let "nobody read it" and "it is coherent" print identically.
    """

    findings = RegisterCoherenceCheck().evaluate(bundle())

    assert len(findings) == 1
    assert "unverified, not coherent" in findings[0].summary
    assert findings[0].severity is IntegritySeverity.OBSERVATION
