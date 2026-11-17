import hashlib

from aistack.contracts.artifact import KnowledgeArtifact


HASH_ALGORITHM = "sha256"


def compute_content_hash(
    artifacts: list[KnowledgeArtifact],
) -> str:
    """
    Compute the governed content fingerprint of a bundle.

    The fingerprint is derived from artifact **contents**, read
    from `metadata["content_hash"]`.

    Consequences:
    - it does not depend on generation time;
    - it does not depend on artifact ordering;
    - regenerating a bundle from an unchanged heritage
      always yields the same value.

    This is what allows a consumer to prove that a bundle
    obtained from a mirror is equivalent to the bundle
    produced from the governance SPOT.

    **It read `artifact.id` until 2026-08-23**, which worked only
    because that field held the content hash. When `id` became
    the governed identifier (GOV-0002/OS-021), the same code
    would have fingerprinted the *names* instead: two bundles
    carrying the same 65 identifiers over different content would
    have hashed identically, and the mirror equivalence this
    exists for would have quietly stopped meaning anything.

    An artifact whose content hash is missing falls back to its
    identifier, and that is deliberate: a fingerprint computed
    over fewer things is weaker, but a fingerprint that silently
    skipped an artifact would be wrong.
    """

    digest = hashlib.sha256()

    for fingerprint in sorted(
        artifact.metadata.get("content_hash") or artifact.id
        for artifact in artifacts
    ):
        digest.update(
            fingerprint.encode("utf-8")
        )

        digest.update(b"\n")

    return digest.hexdigest()
