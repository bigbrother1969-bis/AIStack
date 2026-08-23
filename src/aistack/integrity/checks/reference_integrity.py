import yaml

from aistack.contracts.context_bundle import ContextBundle
from aistack.contracts.integrity_check import IntegrityCheck
from aistack.contracts.integrity_finding import (
    IntegrityFinding,
    IntegritySeverity,
)


def frontmatter(content: str) -> dict | None:
    """
    The governance block an artifact carries, or `None`.

    Read from `content` because that is where it survives.
    **`KnowledgeArtifact.id` is not the governed identifier** —
    the builder sets it to the content hash, so a bundle holds 65
    artifacts identified by SHA-256 and `FDN-0003` appears
    nowhere in the model. That is recorded as GOV-0002/OS-021;
    this check reads the frontmatter rather than waiting for it.
    """

    if not content.startswith("---"):
        return {}

    parts = content.split("---", 2)

    if len(parts) < 3:
        return None

    try:
        data = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return None

    return data if isinstance(data, dict) else None


def declared_identifier(content: str) -> str | None:
    """The `id` an artifact declares, not the hash it is keyed by."""

    data = frontmatter(content)

    if not data:
        return None

    artifact = data.get("artifact")

    if not isinstance(artifact, dict):
        return None

    declared = artifact.get("id")

    return str(declared) if declared else None


def declared_references(content: str) -> list[str] | None:
    """
    The identifiers an artifact says it references.

    Returns the list, or `None` when the frontmatter could not be
    read at all — which is not the same as an artifact that
    references nothing, and is reported as its own fact.
    """

    data = frontmatter(content)

    if data is None:
        return None

    if not data:
        return []

    relations = data.get("relations")

    if not isinstance(relations, dict):
        return []

    references = relations.get("references")

    if references is None:
        return []

    if not isinstance(references, list):
        return None

    return [str(r) for r in references]


class ReferenceIntegrityCheck(IntegrityCheck):
    """
    Observe references that designate no artifact of the bundle.

    A reference is how the heritage states that two artifacts
    belong together. One pointing at an identifier nothing
    declares states a relationship that does not exist, and until
    2026-08-23 nothing compared the two sets.

    That was not theoretical. Five artifacts declared
    `- PRINCIPLES-REGISTRY` while the registry's identifier was
    `FDN-PRINCIPLES`; four of the five were C3, including the
    Manifesto. They were found by hand, while renaming the
    registry for an unrelated reason (GOV-0002/OS-006), and they
    had been wrong for as long as anyone had looked.

    **The severity is OBSERVATION, and the owner chose it.** A
    `WARNING` would make `clean: False` and fail STD-0300
    criterion 2.6 until every reference resolves, which would
    also forbid committing an artifact that cites a document
    being written. The fact is published at every projection;
    what to do about it stays a judgement.

    Both directions are reported separately. A dangling reference
    is a statement that is wrong; an unreadable frontmatter is a
    statement that could not be read, and reporting them together
    would let "no broken references" and "nobody could tell" read
    identically.
    """

    @property
    def name(self) -> str:
        return "reference-integrity"

    def evaluate(
        self,
        bundle: ContextBundle,
    ) -> list[IntegrityFinding]:

        # The governed identifiers, read from the frontmatter.
        # `artifact.id` is a content hash (OS-021), so comparing
        # against it would report every reference in the heritage
        # as dangling — which is exactly what a first version of
        # this check did: 85 of them, including `FDN-0003` cited
        # twelve times.
        declared = {
            identifier
            for identifier in (
                declared_identifier(artifact.content)
                for artifact in bundle.artifacts
            )
            if identifier
        }

        dangling: list[str] = []
        unreadable: list[str] = []

        for artifact in bundle.artifacts:

            references = declared_references(artifact.content)

            name = declared_identifier(artifact.content) or artifact.source

            if references is None:
                unreadable.append(name)
                continue

            for reference in references:
                if reference not in declared:
                    dangling.append(f"{name} → {reference}")

        findings: list[IntegrityFinding] = []

        if dangling:
            findings.append(
                IntegrityFinding(
                    check=self.name,
                    severity=IntegritySeverity.OBSERVATION,
                    summary=(
                        f"{len(dangling)} declared reference(s) "
                        f"designate no artifact of this bundle"
                    ),
                    affected=len(dangling),
                    total=len(bundle.artifacts),
                    unit="references",
                    subjects=tuple(sorted(dangling)),
                )
            )

        if unreadable:
            findings.append(
                IntegrityFinding(
                    check=self.name,
                    severity=IntegritySeverity.OBSERVATION,
                    summary=(
                        f"{len(unreadable)} artifact(s) declare "
                        f"relations this check could not read; their "
                        f"references are unverified, not absent"
                    ),
                    affected=len(unreadable),
                    total=len(bundle.artifacts),
                    unit="artifacts",
                    subjects=tuple(sorted(unreadable)),
                )
            )

        return findings
