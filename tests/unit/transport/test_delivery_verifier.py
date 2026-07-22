from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

from aistack.transport.delivery_verifier import DeliveryVerifier


def test_verify_returns_true_when_destination_exists() -> None:
    writer = Mock()
    writer.exists.return_value = True

    capability = SimpleNamespace(writer=writer)
    destination_resource = object()
    request = SimpleNamespace(
        destination_resource=destination_resource,
    )
    result = Mock()

    verifier = DeliveryVerifier()

    verified = verifier.verify(
        capability=capability,
        request=request,
        result=result,
    )

    assert verified is True
    writer.exists.assert_called_once_with(destination_resource)


def test_verify_returns_false_when_destination_does_not_exist() -> None:
    writer = Mock()
    writer.exists.return_value = False

    capability = SimpleNamespace(writer=writer)
    destination_resource = object()
    request = SimpleNamespace(
        destination_resource=destination_resource,
    )
    result = Mock()

    verifier = DeliveryVerifier()

    verified = verifier.verify(
        capability=capability,
        request=request,
        result=result,
    )

    assert verified is False
    writer.exists.assert_called_once_with(destination_resource)
