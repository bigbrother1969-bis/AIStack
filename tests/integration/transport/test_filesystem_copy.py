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


def test_copy_python_file(tmp_path):

    source = Path("tests/data/example.py")
    destination = tmp_path / "example-copy.py"

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
        # tmp_path is disposed of by pytest; nothing of this
        # test ever exists inside the repository (STD-0002).
        destination.unlink(missing_ok=True)


def test_copy_binary_file(tmp_path):

    source = Path("tests/data/example.bin")
    destination = tmp_path / "example-copy.bin"

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
        # tmp_path is disposed of by pytest; nothing of this
        # test ever exists inside the repository (STD-0002).
        destination.unlink(missing_ok=True)
