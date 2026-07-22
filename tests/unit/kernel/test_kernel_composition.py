from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from aistack.kernel.bootstrap.default import create_kernel
from aistack.kernel.context import Kernel
from aistack.kernel.registries import KernelRegistries
from aistack.kernel.services import KernelServices
from aistack.transport.default_transport_engine import (
    DefaultTransportEngine,
)
from aistack.transport.delivery_verifier import DeliveryVerifier
from aistack.transport.registry.in_memory_transport_registry import (
    InMemoryTransportRegistry,
)


def test_create_kernel_composes_expected_runtime_graph() -> None:
    kernel = create_kernel()

    assert isinstance(kernel, Kernel)
    assert isinstance(kernel.registries, KernelRegistries)
    assert isinstance(kernel.services, KernelServices)

    assert isinstance(
        kernel.services.transport_registry,
        InMemoryTransportRegistry,
    )
    assert isinstance(
        kernel.services.delivery_verifier,
        DeliveryVerifier,
    )
    assert isinstance(
        kernel.services.transport,
        DefaultTransportEngine,
    )


def test_kernel_services_expose_shared_transport_dependencies() -> None:
    kernel = create_kernel()
    transport = kernel.services.transport

    assert transport._registry is kernel.services.transport_registry
    assert (
        transport._delivery_verifier
        is kernel.services.delivery_verifier
    )


def test_kernel_runtime_graph_is_structurally_immutable() -> None:
    kernel = create_kernel()

    with pytest.raises(FrozenInstanceError):
        kernel.services = kernel.services

    with pytest.raises(FrozenInstanceError):
        kernel.registries.providers = kernel.registries.providers

    with pytest.raises(FrozenInstanceError):
        kernel.services.transport = kernel.services.transport
