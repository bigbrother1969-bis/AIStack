import re

from aistack.contracts.classification import DOMAIN_PREFIXES
from aistack.contracts.context_bundle import ContextBundle
from aistack.contracts.integrity_check import IntegrityCheck
from aistack.contracts.integrity_finding import (
    IntegrityFinding,
    IntegritySeverity,
)


REGISTRY = "FDN-0012"


ROW = re.compile(r"^\|\s*([^|]+?)\s*\|")

TABLE_HEADER = re.compile(r"^\|\s*ID\s*\|")

GOVERNED_FORM = re.compile(
    r"^(" + "|".join(sorted(DOMAIN_PREFIXES)) + r")-P-\d{3}$"
)

# Anything shaped like a principle identifier, governed prefix or
# not, so that `KNW-P-001` is reported rather than skipped as
# unrecognised. A check that only sees what it expects reports
# nothing about what it does not.
CITATION = re.compile(r"\b[A-Z]{2,5}-P-\d+\b")


def registry_of(bundle: ContextBundle):
    """The artifact declaring the principles, or `None`."""

    for artifact in bundle.artifacts:
        if artifact.id == REGISTRY:
            return artifact

    return None


def registered_identifiers(content: str) -> list[str]:
    """
    The first cell of every row of every `| ID | ... |` table.

    Read positionally rather than by pattern, and that is the
    whole point: a check that collected cells *matching*
    `<DOMAIN>-P-NNN` would find only conforming identifiers and
    would report a malformed one as absent rather than as wrong.

    Rows outside those tables are ignored. FDN-0012 carries a
    two-column table of the 2026-08-21 renumbering, quoting the
    old three-digit forms it retired; reading those as
    declarations would make the registry's own account of its
    history a violation of the rule that history established.
    """

    identifiers: list[str] = []
    inside = False

    for line in content.splitlines():

        if TABLE_HEADER.match(line):
            inside = True
            continue

        if not line.startswith("|"):
            inside = False
            continue

        if not inside:
            continue

        cell = ROW.match(line)

        if not cell:
            continue

        value = cell.group(1).strip()

        if not value or set(value) <= set("-: "):
            continue

        identifiers.append(value)

    return identifiers


def cited_identifiers(bundle: ContextBundle) -> dict[str, list[str]]:
    """Every `<X>-P-<N>` token in the heritage, and who wrote it."""

    citations: dict[str, set[str]] = {}

    for artifact in bundle.artifacts:
        for token in CITATION.findall(artifact.content):
            citations.setdefault(token, set()).add(artifact.source)

    return {
        token: sorted(sources)
        for token, sources in citations.items()
    }


class PrincipleIdentifierCheck(IntegrityCheck):
    """
    Observe the identifiers of the principles registry.

    STD-0102 gives a principle the form `<DOMAIN>-P-NNN` and an
    artifact the form `<DOMAIN>-NNNN`. The `P` is what stops
    `FDN-0011` (Contract-Based Engineering, an artifact) from
    being confused with `FDN-011` (a principle), which is not
    hypothetical: fifteen such pairs existed until 2026-08-21,
    and the collision became real when `FDN-0011` was registered.

    The renumbering that fixed it **missed the Operations
    family** — four principles and one citation — and the gap
    survived a day because nothing read the registry. That is
    GOV-0002/OS-005, and this check is what closes it.

    Two facts are published, and they are different questions:

    - a **registered** identifier that does not carry the
      governed form. Writing `FDN-006` into the registry
      tomorrow would otherwise pass every check;
    - a **cited** identifier that the registry does not declare.
      102 citations across the heritage designate 49 principles;
      a citation resolving to nothing states a rule that no
      registry governs.

    **What is deliberately not checked is the old form in
    prose.** Every three-digit occurrence left in the heritage —
    fourteen, measured 2026-08-23 — is a deliberate quotation:
    FDN-0012 and STD-0102 both recount the renumbering, and they
    cannot do so without naming what they retired. A check over
    prose cannot tell a quotation from a live citation, and would
    report a heritage that documents its history as one that
    failed to migrate.

    **The two facts carry different severities, and the second
    was corrected on the day it was written.**

    A malformed registered identifier is a `WARNING`: the form is
    decided, the registry is a single table, and there is no
    state of the work in which a principle is registered under a
    name the standard forbids.

    A citation the registry does not declare is an
    `OBSERVATION`. It was a `WARNING` for four hours, and it
    fired on the commit that qualified this entry's own family —
    the register recorded a decision to create `FDN-P-015` and
    `ENG-P-007` before the rows existed, and `clean: False`
    forbade recording the decision before its consequence.

    That is the same asymmetry `reference-integrity` was given
    `OBSERVATION` for on 2026-08-23: a document may legitimately
    cite one being written, and a heritage whose method is
    *decide, record, then execute* must be able to commit the
    middle step. The occurrence OS-005 was opened for — a
    citation of `OPS-004` left behind by the renumbering — is
    still published at every projection, which is what would
    have caught it a day earlier.
    """

    @property
    def name(self) -> str:
        return "principle-identifiers"

    def evaluate(
        self,
        bundle: ContextBundle,
    ) -> list[IntegrityFinding]:

        registry = registry_of(bundle)

        if registry is None:
            # Not a silent pass, and not a warning either. A
            # partial bundle legitimately carries no registry,
            # so this states what was *not* measured — the same
            # answer `contract-debt` gives to a projection with
            # no inventory. "Nobody read it" and "it conforms"
            # must not print identically; whether a projection
            # ought to carry FDN-0012 is asserted over the real
            # heritage, by the integration suite, where the
            # question has an answer.
            return [
                IntegrityFinding(
                    check=self.name,
                    severity=IntegritySeverity.OBSERVATION,
                    summary=(
                        f"{REGISTRY} is absent from this bundle; "
                        f"the principle identifiers are "
                        f"unverified, not conforming"
                    ),
                    affected=len(bundle.artifacts),
                    total=len(bundle.artifacts),
                )
            ]

        registered = registered_identifiers(registry.content)

        malformed = [
            identifier
            for identifier in registered
            if not GOVERNED_FORM.match(identifier)
        ]

        declared = set(registered) - set(malformed)

        unregistered = {
            token: sources
            for token, sources in cited_identifiers(bundle).items()
            if token not in declared
        }

        findings: list[IntegrityFinding] = []

        if malformed:
            findings.append(
                IntegrityFinding(
                    check=self.name,
                    severity=IntegritySeverity.WARNING,
                    summary=(
                        f"{len(malformed)} registered principle(s) "
                        f"do not carry the governed form "
                        f"<DOMAIN>-P-NNN "
                        f"({' · '.join(sorted(DOMAIN_PREFIXES))})"
                    ),
                    affected=len(malformed),
                    total=len(registered),
                    unit="principles",
                    subjects=tuple(sorted(malformed)),
                )
            )

        if unregistered:
            findings.append(
                IntegrityFinding(
                    check=self.name,
                    severity=IntegritySeverity.OBSERVATION,
                    summary=(
                        f"{len(unregistered)} cited principle(s) "
                        f"are declared by no row of {REGISTRY}"
                    ),
                    affected=len(unregistered),
                    total=len(registered),
                    unit="principles",
                    subjects=tuple(
                        f"{token} ← {', '.join(sources)}"
                        for token, sources in sorted(
                            unregistered.items()
                        )
                    ),
                )
            )

        return findings
