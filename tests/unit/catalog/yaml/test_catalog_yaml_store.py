from pathlib import Path

import pytest

from aistack.catalog.yaml import load_catalog_yaml, save_catalog_yaml
from aistack.kernel.catalog import Catalog, CatalogItem


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_a_complete_catalog_is_loaded(tmp_path: Path):
    path = write(
        tmp_path / "catalog.yml",
        """
        catalog_id: docker-runtime
        title: Docker Runtime Catalog
        metadata:
          source_provider: aistack.provider.docker
        items:
          - id: jellyfin
            label: jellyfin
            kind: container
            source: jellyfin:latest
            metadata:
              status: Up 3 days
        """,
    )

    catalog = load_catalog_yaml(path)

    assert isinstance(catalog, Catalog)
    assert catalog.catalog_id == "docker-runtime"
    assert catalog.title == "Docker Runtime Catalog"
    assert catalog.metadata == {"source_provider": "aistack.provider.docker"}
    assert len(catalog.items) == 1

    item = catalog.items[0]
    assert item.id == "jellyfin"
    assert item.label == "jellyfin"
    assert item.kind == "container"
    assert item.source == "jellyfin:latest"
    assert item.metadata == {"status": "Up 3 days"}


def test_items_is_a_tuple_matching_what_catalog_declares(tmp_path: Path):
    """
    `Catalog.items: tuple[CatalogItem, ...]` — until 2026-09-10 this
    loader built it as a list comprehension, which Python's own
    dataclass machinery accepts without complaint (a declared field
    type is not enforced at runtime). `mypy` found the mismatch on
    its first run against this codebase.
    """

    path = write(
        tmp_path / "catalog.yml",
        """
        catalog_id: docker-runtime
        title: Docker Runtime Catalog
        items: []
        """,
    )

    assert isinstance(load_catalog_yaml(path).items, tuple)


def test_a_label_defaults_to_the_items_own_id(tmp_path: Path):
    path = write(
        tmp_path / "catalog.yml",
        """
        catalog_id: docker-runtime
        title: Docker Runtime Catalog
        items:
          - id: jellyfin
        """,
    )

    assert load_catalog_yaml(path).items[0].label == "jellyfin"


def test_kind_source_and_metadata_default_when_absent(tmp_path: Path):
    path = write(
        tmp_path / "catalog.yml",
        """
        catalog_id: docker-runtime
        title: Docker Runtime Catalog
        items:
          - id: jellyfin
        """,
    )

    item = load_catalog_yaml(path).items[0]

    assert item.kind == ""
    assert item.source == ""
    assert item.metadata == {}


def test_a_catalog_with_no_items_is_valid(tmp_path: Path):
    path = write(
        tmp_path / "catalog.yml",
        """
        catalog_id: docker-runtime
        title: Docker Runtime Catalog
        """,
    )

    catalog = load_catalog_yaml(path)
    assert catalog.items == ()


def test_metadata_defaults_to_empty_when_absent(tmp_path: Path):
    path = write(
        tmp_path / "catalog.yml",
        """
        catalog_id: docker-runtime
        title: Docker Runtime Catalog
        """,
    )

    assert load_catalog_yaml(path).metadata == {}


def test_a_catalog_that_is_not_a_mapping_is_refused(tmp_path: Path):
    path = write(tmp_path / "list.yml", "- one\n- two\n")

    with pytest.raises(ValueError, match="mapping"):
        load_catalog_yaml(path)


def test_saving_and_reloading_round_trips_a_catalog(tmp_path: Path):
    original = Catalog(
        catalog_id="docker-runtime",
        title="Docker Runtime Catalog",
        metadata={"source_provider": "aistack.provider.docker"},
        items=(
            CatalogItem(
                id="jellyfin",
                label="jellyfin",
                kind="container",
                source="jellyfin:latest",
                metadata={"status": "Up 3 days"},
            ),
        ),
    )

    path = tmp_path / "round_trip.yml"
    save_catalog_yaml(original, path)

    assert load_catalog_yaml(path) == original


def test_saving_creates_missing_parent_directories(tmp_path: Path):
    original = Catalog(catalog_id="x", title="x", items=())

    path = tmp_path / "nested" / "dir" / "catalog.yml"
    save_catalog_yaml(original, path)

    assert path.exists()
