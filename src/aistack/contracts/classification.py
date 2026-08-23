from enum import Enum

from aistack.contracts.undeclared import UNDECLARED


class KnowledgeDomain(str, Enum):
    FOUNDATION = "Foundation"
    ARCHITECTURE = "Architecture"
    GOVERNANCE = "Governance"
    STANDARDS = "Standards"
    ENGINEERING = "Engineering"
    OPERATIONS = "Operations"
    KNOWLEDGE_ASSETS = "Knowledge Assets"


DOMAIN_PREFIXES: dict[str, str] = {
    "FDN": KnowledgeDomain.FOUNDATION.value,
    "ARC": KnowledgeDomain.ARCHITECTURE.value,
    "GOV": KnowledgeDomain.GOVERNANCE.value,
    "STD": KnowledgeDomain.STANDARDS.value,
    "ENG": KnowledgeDomain.ENGINEERING.value,
    "OPS": KnowledgeDomain.OPERATIONS.value,
}
"""
The three-letter prefix each domain uses in an identifier.

STD-0102 governs the form `<DOMAIN>-P-NNN` for a principle. That
form needs a closed set of domain prefixes, and until 2026-08-23
the set existed only as the identifiers people had happened to
write.

`Knowledge Assets` is absent, and that is a fact about the
heritage rather than an oversight: no principle has been
registered in it, so no prefix has been decided. Inventing one
here would be this module deciding a naming question, which
GOV-P-001 places with the owner.
"""


class SemanticType(str, Enum):
    PRINCIPLE = "Principle"
    RULE = "Rule"
    POLICY = "Policy"
    ADR = "ADR"
    STANDARD = "Standard"
    SPECIFICATION = "Specification"
    KNOWLEDGE_ARTIFACT = "Knowledge Artifact"


def _normalize(value, vocabulary) -> str:
    """
    Match a declared value against a closed vocabulary.

    Matching ignores case and surrounding whitespace, because a
    human writing "foundation" means Foundation. It does not
    guess beyond that: a value outside the vocabulary is
    reported as undeclared, never mapped to the nearest
    plausible term.

    That an out-of-vocabulary declaration and a missing one both
    read as "unknown" here is deliberate. The contract carries
    canonical values only; telling the two apart is the
    validator's work, done against the frontmatter where the
    invalid value is still visible.
    """

    if value is None:
        return UNDECLARED

    text = str(value).strip()

    if not text:
        return UNDECLARED

    for member in vocabulary:
        if member.value.casefold() == text.casefold():
            return member.value

    return UNDECLARED


def normalize_domain(value) -> str:
    """
    Return a declared knowledge domain, or "unknown".

    Per FDN-0003 Article 4 the domain is declared by a human and
    read here. Nothing about the artifact's path, filename or
    content is consulted.
    """

    return _normalize(value, KnowledgeDomain)


def normalize_semantic_type(value) -> str:
    """
    Return a declared semantic type, or "unknown".

    STD-0100 v2.0 separates `semantic_type` — this closed
    vocabulary — from `type`, the free descriptive label an
    artifact gives itself. Only the former is normalized; the
    latter is preserved verbatim, because it carries a
    distinction the vocabulary does not.
    """

    return _normalize(value, SemanticType)
