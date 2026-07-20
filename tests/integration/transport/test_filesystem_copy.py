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
from aistack.transport.filesystem.filesystem_writer import (
    FilesystemWriter,
)


def test_copy_python_file(tmp_path):

    source = Path("tests/data/example.py")
    destination = tmp_path / "copy.py"

    repository = FilesystemPathRepository(
        {
            "source": source,
            "destination": destination,
        }
    )

    path_resolver = FilesystemPathResolver(repository)

    receiver = FilesystemReceiver(path_resolver)
    writer = FilesystemWriter(path_resolver)

    data = receiver.receive(
        ResourceReference(
            resource_type="python",
            resource_id="source",
        )
    )

    writer.write(
        ResourceReference(
            resource_type="python",
            resource_id="destination",
        ),
        data,
    )

    assert destination.exists()
    assert destination.read_bytes() == source.read_bytes()


def test_copy_binary_file(tmp_path):

    source = Path("tests/data/example.bin")
    destination = tmp_path / "copy.bin"

    repository = FilesystemPathRepository(
        {
            "source": source,
            "destination": destination,
        }
    )

    path_resolver = FilesystemPathResolver(repository)

    receiver = FilesystemReceiver(path_resolver)
    writer = FilesystemWriter(path_resolver)

    data = receiver.receive(
        ResourceReference(
            resource_type="binary",
            resource_id="source",
        )
    )

    writer.write(
        ResourceReference(
            resource_type="binary",
            resource_id="destination",
        ),
        data,
    )

    assert destination.exists()
    assert destination.read_bytes() == source.read_bytes()
