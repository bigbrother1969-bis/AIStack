from dataclasses import FrozenInstanceError
from datetime import datetime, timezone

import pytest

from aistack.kernel.time import Provenance, Snapshot, VersionId


def test_snapshot_carries_content_version_provenance_and_instant() -> None:
    observed_at = datetime(2026, 9, 10, 12, 0, 0, tzinfo=timezone.utc)

    snapshot: Snapshot[dict[str, bool]] = Snapshot(
        content={"ok": True},
        version=VersionId(subject="docker-runtime", sequence=1),
        provenance=Provenance(origin="aistack.provider.docker"),
        observed_at=observed_at,
    )

    assert snapshot.content == {"ok": True}
    assert snapshot.version == VersionId(subject="docker-runtime", sequence=1)
    assert snapshot.provenance.origin == "aistack.provider.docker"
    assert snapshot.observed_at == observed_at


def test_snapshot_is_immutable() -> None:
    snapshot: Snapshot[str] = Snapshot(
        content="payload",
        version=VersionId(subject="s", sequence=1),
        provenance=Provenance(origin="test"),
        observed_at=datetime.now(timezone.utc),
    )

    with pytest.raises(FrozenInstanceError):
        snapshot.content = "changed"


def test_snapshot_is_generic_over_arbitrary_content_types() -> None:
    """
    A `Snapshot[ExecutionTrace]` and a `Snapshot[ApplyReport]` share
    nothing but this contract — the reason `content` is generic
    rather than typed to one payload shape.
    """

    class Payload:
        def __init__(self, value: int) -> None:
            self.value = value

    snapshot: Snapshot[Payload] = Snapshot(
        content=Payload(42),
        version=VersionId(subject="s", sequence=1),
        provenance=Provenance(origin="test"),
        observed_at=datetime.now(timezone.utc),
    )

    assert snapshot.content.value == 42
