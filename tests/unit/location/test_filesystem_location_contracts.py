from pathlib import Path
from types import SimpleNamespace
from typing import cast

from aistack.location import LocationRepository, LocationResolver
from aistack.path.filesystem.filesystem_location_repository import (
    FilesystemLocationRepository,
)
from aistack.path.filesystem.filesystem_location_resolver import (
    FilesystemLocationResolver,
)
from aistack.transport.contracts.resource_reference import ResourceReference


def test_filesystem_repository_supports_location_contract() -> None:
    expected_path = Path("/tmp/resource")
    repository = FilesystemLocationRepository(
        mappings={"resource-1": expected_path},
    )
    resource = cast(
        ResourceReference,
        SimpleNamespace(resource_id="resource-1"),
    )

    location_repository: LocationRepository = repository

    assert location_repository.locate(resource) == expected_path
    assert repository.get("resource-1") == expected_path


def test_filesystem_resolver_supports_location_contract() -> None:
    expected_path = Path("/tmp/resource")
    repository = FilesystemLocationRepository(
        mappings={"resource-1": expected_path},
    )
    resolver = FilesystemLocationResolver(repository)
    resource = cast(
        ResourceReference,
        SimpleNamespace(resource_id="resource-1"),
    )

    location_resolver: LocationResolver = resolver

    assert location_resolver.resolve(resource) == expected_path
