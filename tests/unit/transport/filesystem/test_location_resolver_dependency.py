from __future__ import annotations

from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from typing import cast

from aistack.transport.contracts.resource_reference import ResourceReference
from aistack.transport.filesystem.filesystem_receiver import FilesystemReceiver
from aistack.transport.filesystem.filesystem_writer import FilesystemWriter


class StubLocationResolver:
    def __init__(self, locations: dict[str, Path]) -> None:
        self._locations = locations

    def resolve(self, resource: ResourceReference) -> Path:
        return self._locations[resource.resource_id]


def resource_reference(resource_id: str) -> ResourceReference:
    return cast(
        ResourceReference,
        SimpleNamespace(resource_id=resource_id),
    )


def test_filesystem_receiver_depends_on_location_resolver(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.bin"
    source.write_bytes(b"governed knowledge")

    resolver = StubLocationResolver({"source": source})
    receiver = FilesystemReceiver(resolver)

    with receiver.open(resource_reference("source")) as stream:
        assert stream.read() == b"governed knowledge"


def test_filesystem_writer_depends_on_location_resolver(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "nested" / "destination.bin"

    resolver = StubLocationResolver({"destination": destination})
    writer = FilesystemWriter(resolver)
    resource = resource_reference("destination")

    writer.write(resource, BytesIO(b"governed knowledge"))

    assert destination.read_bytes() == b"governed knowledge"
    assert writer.exists(resource)
