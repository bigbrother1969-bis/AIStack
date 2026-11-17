"""The materialisation goes through the Kernel's transaction service (`ADR-0027` § 11)."""

from __future__ import annotations

from pathlib import Path

import pytest

from aistack.catalog.filesystem import MediaLibraryCatalogBuilder
from aistack.kernel.bootstrap.default import create_kernel
from aistack.providers.filesystem import DEFAULT_MEDIA_EXTENSIONS, MediaLibraryProvider
from aistack.selection.capacity import assess_capacity
from aistack.selection.materialise import MaterialisationFailed, materialise_selection
from aistack.selection.subtree import resolve_subtrees
from aistack.transaction.contracts.selection_materialise import KIND
from aistack.transaction.engines.selection_materialise import SelectionMaterialiseEngine


def _library(tmp_path: Path) -> Path:
    root = tmp_path / "library"
    (root / "Bach").mkdir(parents=True)
    (root / "Bach" / "01.mp3").write_bytes(b"bach")
    return root


def _materialise(transactions, root: Path, target: Path):
    catalog = MediaLibraryCatalogBuilder(catalog_id="music-library", title="Music").build(
        MediaLibraryProvider(root).collect()
    )
    resolution = resolve_subtrees(catalog, ["Bach"])
    return materialise_selection(
        transactions, catalog, resolution, assess_capacity(resolution, 0), target, DEFAULT_MEDIA_EXTENSIONS
    )


def test_the_kernel_knows_the_operation() -> None:
    assert create_kernel().services.transactions.registry.get(KIND) is not None


def test_the_folder_is_brought_to_the_selection_by_the_transaction(tmp_path: Path) -> None:
    root = _library(tmp_path)
    target = tmp_path / "phone"

    report = _materialise(create_kernel().services.transactions, root, target)

    assert report.linked == ("Bach/01.mp3",)
    assert (target / "Bach" / "01.mp3").stat().st_ino == (root / "Bach" / "01.mp3").stat().st_ino


def test_a_refusal_comes_back_as_a_report_and_writes_nothing(tmp_path: Path) -> None:
    target = tmp_path / "phone"

    report = _materialise(create_kernel().services.transactions, tmp_path / "gone", target)

    assert "library root does not exist" in report.refused
    assert not target.exists()


def test_another_payload_is_refused() -> None:
    with pytest.raises(TypeError):
        SelectionMaterialiseEngine().execute("not a selection")


def test_a_failed_transaction_says_so(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def broken(self, payload):  # noqa: ANN001
        raise RuntimeError("the disk went away")

    monkeypatch.setattr(SelectionMaterialiseEngine, "execute", broken)

    with pytest.raises(MaterialisationFailed) as raised:
        _materialise(create_kernel().services.transactions, _library(tmp_path), tmp_path / "phone")

    assert "the disk went away" in raised.value.error
