from pathlib import Path

from aistack.path.filesystem.filesystem_location_repository import (
    FilesystemLocationRepository,
)
from aistack.path.filesystem.filesystem_location_resolver import (
    FilesystemLocationResolver,
)
from aistack.transport.contracts.resource_reference import ResourceReference
from aistack.transport.filesystem.filesystem_receiver import (
    FilesystemReceiver,
)


def build_receiver(path: Path) -> FilesystemReceiver:
    repository = FilesystemLocationRepository(
        {
            "resource": path,
        }
    )

    resolver = FilesystemLocationResolver(repository)

    return FilesystemReceiver(resolver)


def test_receive_python_file():

    resource = Path("tests/data/example.py")

    receiver = build_receiver(resource)

    with receiver.open(
        ResourceReference(
            resource_type="python",
            resource_id="resource",
        )
    ) as stream:
        data = stream.read()

    assert data == resource.read_bytes()


def test_receive_binary_file():

    resource = Path("tests/data/example.bin")

    receiver = build_receiver(resource)

    with receiver.open(
        ResourceReference(
            resource_type="binary",
            resource_id="resource",
        )
    ) as stream:
        data = stream.read()

    assert data == resource.read_bytes()
