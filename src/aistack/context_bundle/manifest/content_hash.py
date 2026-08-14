import hashlib

from aistack.contracts.artifact import KnowledgeArtifact


HASH_ALGORITHM = "sha256"


def compute_content_hash(
    artifacts: list[KnowledgeArtifact],
) -> str:
    """
    Compute the governed content fingerprint of a bundle.

    The fingerprint is derived from artifact identities only.

    Consequences:
    - it does not depend on generation time;
    - it does not depend on artifact ordering;
    - regenerating a bundle from an unchanged heritage
      always yields the same value.

    This is what allows a consumer to prove that a bundle
    obtained from a mirror is equivalent to the bundle
    produced from the governance SPOT.
    """

    digest = hashlib.sha256()

    for artifact_id in sorted(
        artifact.id
        for artifact in artifacts
    ):
        digest.update(
            artifact_id.encode("utf-8")
        )

        digest.update(b"\n")

    return digest.hexdigest()
