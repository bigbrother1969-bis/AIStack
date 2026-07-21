"""Tests for Knowledge Transport Layer public data contracts."""

from dataclasses import FrozenInstanceError

import pytest

from aistack.transport import (
    DeliveryMode,
    KnowledgeArtifact,
    ResourceReference,
    TransportEndpoint,
    TransportRequest,
    TransportResult,
    TransportStatus,
)


def build_artifact() -> KnowledgeArtifact:
    return KnowledgeArtifact(
        artifact_id="ART-0001",
        name="example.md",
        media_type="text/markdown",
        size_bytes=42,
        sha256="a" * 64,
        metadata={"owner": "Foundation"},
    )


def build_resource() -> ResourceReference:
    return ResourceReference(
        resource_type="knowledge_artifact",
        resource_id="ART-0001",
    )


def build_source_endpoint() -> TransportEndpoint:
    return TransportEndpoint(
        endpoint_id="SOURCE-0001",
        endpoint_type="filesystem",
        uri="file:///",
        metadata={},
    )


def build_destination_endpoint() -> TransportEndpoint:
    return TransportEndpoint(
        endpoint_id="DESTINATION-0001",
        endpoint_type="filesystem",
        uri="file:///",
        metadata={},
    )


def test_public_contracts_can_describe_a_transport_request() -> None:
    request = TransportRequest(
        resource=build_resource(),
        source=build_source_endpoint(),
        destination=build_destination_endpoint(),
        delivery_mode=DeliveryMode.CREATE,
        correlation_id="CORR-0001",
    )

    assert request.resource.resource_id == "ART-0001"
    assert request.source.endpoint_type == "filesystem"
    assert request.destination.endpoint_type == "filesystem"
    assert request.delivery_mode is DeliveryMode.CREATE
    assert request.correlation_id == "CORR-0001"


def test_public_contracts_can_describe_a_transport_result() -> None:
    result = TransportResult(
        transaction_id="TX-0001",
        status=TransportStatus.DELIVERED,
        delivered=True,
        verified=False,
        rollback_available=False,
        message="Resource delivered but not yet verified.",
    )

    assert result.transaction_id == "TX-0001"
    assert result.delivered is True
    assert result.verified is False
    assert result.rollback_available is False
    assert result.status is TransportStatus.DELIVERED


def test_contracts_are_immutable() -> None:
    artifact = build_artifact()
    resource = build_resource()

    request = TransportRequest(
        resource=resource,
        source=build_source_endpoint(),
        destination=build_destination_endpoint(),
        delivery_mode=DeliveryMode.CREATE,
    )

    with pytest.raises(FrozenInstanceError):
        artifact.name = "modified.md"  # type: ignore[misc]

    with pytest.raises(FrozenInstanceError):
        resource.resource_id = "ART-0002"  # type: ignore[misc]

    with pytest.raises(FrozenInstanceError):
        request.correlation_id = "CORR-0002"  # type: ignore[misc]


def test_transport_status_contains_recovery_states() -> None:
    assert TransportStatus.ROLLED_BACK.value == "rolled_back"
    assert TransportStatus.REDELIVERED.value == "redelivered"
