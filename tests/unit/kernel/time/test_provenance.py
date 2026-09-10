from dataclasses import FrozenInstanceError

import pytest

from aistack.kernel.time import Provenance


def test_provenance_carries_origin_only_by_default() -> None:
    provenance = Provenance(origin="aistack.provider.docker")

    assert provenance.origin == "aistack.provider.docker"
    assert provenance.causality is None


def test_provenance_carries_optional_causality() -> None:
    provenance = Provenance(
        origin="KernelRuntime",
        causality="request-001",
    )

    assert provenance.causality == "request-001"


def test_provenance_is_immutable() -> None:
    provenance = Provenance(origin="aistack.provider.docker")

    with pytest.raises(FrozenInstanceError):
        provenance.origin = "changed"
