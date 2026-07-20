from pathlib import Path

from aistack.path.filesystem.filesystem_path_repository import (
    FilesystemPathRepository,
)
from aistack.path.filesystem.filesystem_path_resolver import (
    FilesystemPathResolver,
)
from aistack.transport.contracts.resource_reference import ResourceReference
from aistack.transport.filesystem.filesystem_receiver import (
    FilesystemReceiver,
)


def build_receiver(resource_path: Path) -> FilesystemReceiver:
    repository = FilesystemPathRepository(
        {
            "resource": resource_path,
        }
    )

    path_resolver = FilesystemPathResolver(repository)

    return FilesystemReceiver(path_resolver)


def test_receive_python_file():

    resource = Path("tests/data/example.py")

    receiver = build_receiver(resource)

    data = receiver.receive(
        ResourceReference(
            resource_type="python",
            resource_id="resource",
        )
    )

    assert data == resource.read_bytes()


def test_receive_binary_file():

    resource = Path("tests/data/example.bin")

    receiver = build_receiver(resource)

    data = receiver.receive(
        ResourceReference(
            resource_type="binary",
            resource_id="resource",
        )
    )

    assert data == resource.read_bytes()
