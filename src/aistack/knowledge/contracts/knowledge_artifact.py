"""
Knowledge Artifact contract.
"""

from __future__ import annotations

from dataclasses import dataclass

from aistack.transport.contracts.resource_reference import (
    ResourceReference,
)


@dataclass(frozen=True, slots=True)
class KnowledgeArtifact:
    """
    A governed Knowledge Artifact.

    A Knowledge Artifact represents a governed piece of knowledge.

    The artifact itself is independent from its physical storage.
    The associated ResourceReference identifies where the artifact
    can be obtained.
    """

    id: str

    kind: str

    resource: ResourceReference
