from pathlib import Path

from aistack.location.filesystem.filesystem_location_repository import (
    FilesystemLocationRepository,
)
from aistack.location.filesystem.filesystem_location_resolver import (
    FilesystemLocationResolver,
)
from aistack.transport.contracts.resource_reference import ResourceReference
from aistack.transport.filesystem.filesystem_receiver import (
    FilesystemReceiver,
)
from aistack.transport.filesystem.filesystem_writer import (
    FilesystemWriter,
)


def test_copy_python_file():

    source = Path("tests/data/example.py")
    destination = Path("tests/data/example-copy.py")

    repository = FilesystemLocationRepository(
        {
            "source": source,
            "destination": destination,
        }
    )

    resolver = FilesystemLocationResolver(repository)

    receiver = FilesystemReceiver(resolver)
    writer = FilesystemWriter(resolver)

    try:
        with receiver.open(
            ResourceReference(
                resource_type="python",
                resource_id="source",
            )
        ) as stream:
            writer.write(
                ResourceReference(
                    resource_type="python",
                    resource_id="destination",
                ),
                stream,
            )

        assert destination.read_bytes() == source.read_bytes()

    finally:
        destination.unlink(missing_ok=True)


def test_copy_binary_file():

    source = Path("tests/data/example.bin")
    destination = Path("tests/data/example-copy.bin")

    repository = FilesystemLocationRepository(
        {
            "source": source,
            "destination": destination,
        }
    )

    resolver = FilesystemLocationResolver(repository)

    receiver = FilesystemReceiver(resolver)
    writer = FilesystemWriter(resolver)

    try:
        with receiver.open(
            ResourceReference(
                resource_type="binary",
                resource_id="source",
            )
        ) as stream:
            writer.write(
                ResourceReference(
                    resource_type="binary",
                    resource_id="destination",
                ),
                stream,
            )

        assert destination.read_bytes() == source.read_bytes()

    finally:
        destination.unlink(missing_ok=True)
