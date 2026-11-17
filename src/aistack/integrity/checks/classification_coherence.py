from collections import defaultdict

from aistack.contracts.context_bundle import ContextBundle
from aistack.contracts.integrity_check import IntegrityCheck
from aistack.contracts.integrity_finding import (
    IntegrityFinding,
    IntegritySeverity,
)
from aistack.contracts.undeclared import UNDECLARED


def named(artifact) -> str:
    """
    How an artifact is designated in a finding.

    Its governed identifier since 2026-08-23 (GOV-0002/OS-021),
    falling back to the file it came from — because an artifact
    that declares no identifier still has to be findable by
    whoever must go and fix it.
    """

    identifier = artifact.id

    if identifier and identifier != UNDECLARED:
        return str(identifier)

    return str(artifact.source)


def domains_by_type(
    bundle: ContextBundle,
) -> dict[str, dict[str, list[str]]]:
    """
    For each declared `type`, the domains declared alongside it
    and who declares them.

    An artifact missing either field is not counted. That
    absence is a fact of its own, reported by
    `classification-declaration`, and counting it here would
    make one gap speak twice — and worse, would report a
    *coherence* violation where nothing incoherent was said.
    """

    observed: dict[str, dict[str, list[str]]] = defaultdict(
        lambda: defaultdict(list)
    )

    for artifact in bundle.artifacts:

        declared_type = artifact.declared_type
        domain = artifact.domain

        if not declared_type or declared_type == UNDECLARED:
            continue

        if not domain or domain == UNDECLARED:
            continue

        observed[str(declared_type)][str(domain)].append(
            named(artifact)
        )

    return observed


class ClassificationCoherenceCheck(IntegrityCheck):
    """
    Observe types that answer the domain question twice.

    STD-0100 § *A declared `type` determines its `domain`*:
    every distinct `type` in the heritage maps to exactly one
    `domain`. Two artifacts declaring the same `type` and
    different `domain` values would give the heritage two
    answers to one question.

    The rule was **measured, not decreed**: 2026-08-22 across 63
    artifacts and 16 types, re-measured 2026-08-23 across 65
    artifacts and 19 types, no exception either time. It was
    written into a C2 standard on the first measurement and
    enforced by nothing for a day — recorded as GOV-0002/OS-004,
    and this check is what closes it.

    **The rule is one axis and only one.** STD-0100 names two
    counterexamples that must survive: `FDN-0011` is a
    `Foundation Document` whose `semantic_type` is `Principle`
    where the eight others are `Knowledge Artifact`, and
    `ARCH-0009` is an `Architecture Document` at `C1` where the
    thirteen others are `C2`. A check extended to those axes
    would report both as defects and would be wrong twice. The
    test suite holds that boundary rather than trusting this
    docstring.

    The severity is `WARNING`: unlike a dangling reference,
    which can legitimately precede the document it cites, there
    is no state of the work in which one type belongs to two
    domains. `clean: False` is the correct answer.
    """

    @property
    def name(self) -> str:
        return "classification-coherence"

    def evaluate(
        self,
        bundle: ContextBundle,
    ) -> list[IntegrityFinding]:

        observed = domains_by_type(bundle)

        divergent: list[str] = []

        for declared_type, domains in observed.items():

            if len(domains) < 2:
                continue

            readings = " · ".join(
                f"{domain} ({', '.join(sorted(sources))})"
                for domain, sources in sorted(domains.items())
            )

            divergent.append(f"{declared_type} → {readings}")

        if not divergent:
            return []

        return [
            IntegrityFinding(
                check=self.name,
                severity=IntegritySeverity.WARNING,
                summary=(
                    f"{len(divergent)} declared type(s) map to "
                    f"more than one domain; a type answers that "
                    f"question once"
                ),
                affected=len(divergent),
                total=len(observed),
                unit="types",
                subjects=tuple(sorted(divergent)),
            )
        ]
