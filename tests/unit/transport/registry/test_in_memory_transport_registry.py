from typing import Any

import pytest

from aistack.transport.registry.in_memory_transport_registry import (
    InMemoryTransportRegistry,
)


class DummyCapability:
    @property
    def receiver(self) -> Any:
        return None

    @property
    def writer(self) -> Any:
        return None

    @property
    def verifier(self) -> Any:
        return None


def test_register_and_get():

    registry = InMemoryTransportRegistry()
    capability = DummyCapability()

    registry.register("filesystem", capability)

    assert registry.get("filesystem") is capability


def test_register_duplicate():

    registry = InMemoryTransportRegistry()

    registry.register("filesystem", DummyCapability())

    with pytest.raises(ValueError):
        registry.register("filesystem", DummyCapability())


def test_unknown_transport():

    registry = InMemoryTransportRegistry()

    with pytest.raises(LookupError):
        registry.get("unknown")
