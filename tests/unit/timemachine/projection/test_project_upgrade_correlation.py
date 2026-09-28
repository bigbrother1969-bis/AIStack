"""
`aistack.timemachine.projection.project_upgrade_correlation` —
against real observations recorded through `aistack.providers.docker
.digest_history.record_image_digest` and `.packages_history
.record_package_inventory`, the same "no mocks, real producer"
discipline `test_project_docker_packages.py` already holds.

Every instant below is pinned with the same frozen-`datetime`
monkeypatch `test_project_docker_packages.py`'s own
`test_two_write_on_change_observations_for_one_subject_each_get_their_own_entity`
already uses — the nearest-before/nearest-after pairing this module
computes is exactly the kind of logic that needs real, controlled
instants to verify precisely, not just "two writes, a second apart."
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import aistack.generators.history as history_module
from aistack.history import format_instant
from aistack.providers.docker.digest_history import record_image_digest
from aistack.providers.docker.packages_history import record_package_inventory
from aistack.timemachine.iri import docker_packages_iri
from aistack.timemachine.oxigraph_store import OxigraphGraphStore
from aistack.timemachine.projection import project_upgrade_correlation
from aistack.timemachine.vocabulary import AISTACK_UPGRADE_CORRELATES_WITH

PACKAGES_ONE = [{"name": "bash", "version": "5.2.15-2+b7"}]
PACKAGES_TWO = [{"name": "bash", "version": "5.2.15-3"}]
PACKAGES_THREE = [{"name": "bash", "version": "5.2.21-1"}]


def _frozen_at(instant: datetime) -> type:
    class Frozen(history_module.datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(
                instant.year,
                instant.month,
                instant.day,
                instant.hour,
                instant.minute,
                instant.second,
                tzinfo=tz,
            )

    return Frozen


def _at(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 9, 28, hour, minute, 0, tzinfo=timezone.utc)


def test_no_root_at_all_produces_nothing(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"
    generated_dir.mkdir(parents=True)

    store = OxigraphGraphStore(tmp_path / "graph")
    summary = project_upgrade_correlation(store, generated_dir=generated_dir)

    assert summary.subjects_seen == 0
    assert summary.digest_changes_seen == 0
    assert summary.correlations_written == 0
    assert summary.facts_written == 0


def test_only_digest_root_produces_nothing(tmp_path: Path, monkeypatch):
    generated_dir = tmp_path / "reports" / "generated"
    monkeypatch.setattr(history_module, "datetime", _frozen_at(_at(8)))
    record_image_digest("frigate", "sha256:aaa", generated_dir=generated_dir)

    store = OxigraphGraphStore(tmp_path / "graph")
    summary = project_upgrade_correlation(store, generated_dir=generated_dir)

    assert summary.subjects_seen == 0
    assert summary.correlations_written == 0


def test_only_packages_root_produces_nothing(tmp_path: Path, monkeypatch):
    generated_dir = tmp_path / "reports" / "generated"
    monkeypatch.setattr(history_module, "datetime", _frozen_at(_at(8)))
    record_package_inventory("frigate", "dpkg", PACKAGES_ONE, generated_dir=generated_dir)

    store = OxigraphGraphStore(tmp_path / "graph")
    summary = project_upgrade_correlation(store, generated_dir=generated_dir)

    assert summary.subjects_seen == 0
    assert summary.correlations_written == 0


def test_a_single_digest_observation_is_not_a_change(tmp_path: Path, monkeypatch):
    """
    The first digest ever recorded for a subject has nothing to have
    differed from — `aistack.providers.docker.digest_history
    .record_image_digest`'s own write-on-change contract already
    means it was written unconditionally, not because it changed.
    """

    generated_dir = tmp_path / "reports" / "generated"
    monkeypatch.setattr(history_module, "datetime", _frozen_at(_at(8)))
    record_image_digest("frigate", "sha256:aaa", generated_dir=generated_dir)
    record_package_inventory("frigate", "dpkg", PACKAGES_ONE, generated_dir=generated_dir)

    store = OxigraphGraphStore(tmp_path / "graph")
    summary = project_upgrade_correlation(store, generated_dir=generated_dir)

    assert summary.subjects_seen == 0
    assert summary.digest_changes_seen == 0
    assert summary.correlations_written == 0


def test_one_digest_change_bracketed_by_packages_on_each_side_is_correlated(
    tmp_path: Path, monkeypatch
):
    generated_dir = tmp_path / "reports" / "generated"

    monkeypatch.setattr(history_module, "datetime", _frozen_at(_at(8)))
    record_image_digest("frigate", "sha256:aaa", generated_dir=generated_dir)

    monkeypatch.setattr(history_module, "datetime", _frozen_at(_at(9)))
    record_package_inventory("frigate", "dpkg", PACKAGES_ONE, generated_dir=generated_dir)

    monkeypatch.setattr(history_module, "datetime", _frozen_at(_at(10)))
    record_image_digest("frigate", "sha256:bbb", generated_dir=generated_dir)  # the change

    monkeypatch.setattr(history_module, "datetime", _frozen_at(_at(11)))
    record_package_inventory("frigate", "dpkg", PACKAGES_TWO, generated_dir=generated_dir)

    store = OxigraphGraphStore(tmp_path / "graph")
    summary = project_upgrade_correlation(store, generated_dir=generated_dir)

    assert summary.subjects_seen == 1
    assert summary.digest_changes_seen == 1
    assert summary.correlations_written == 1

    before_entity = docker_packages_iri("frigate", format_instant(_at(9)))
    after_entity = docker_packages_iri("frigate", format_instant(_at(11)))

    links = list(
        store.query(
            f"SELECT ?s ?o WHERE {{ ?s <{AISTACK_UPGRADE_CORRELATES_WITH}> ?o }}"
        )
    )
    assert links == [{"s": before_entity, "o": after_entity}]


def test_two_digest_changes_each_pick_their_own_nearest_packages_pair(
    tmp_path: Path, monkeypatch
):
    generated_dir = tmp_path / "reports" / "generated"

    monkeypatch.setattr(history_module, "datetime", _frozen_at(_at(8)))
    record_image_digest("frigate", "sha256:aaa", generated_dir=generated_dir)

    monkeypatch.setattr(history_module, "datetime", _frozen_at(_at(9)))
    record_package_inventory("frigate", "dpkg", PACKAGES_ONE, generated_dir=generated_dir)

    monkeypatch.setattr(history_module, "datetime", _frozen_at(_at(10)))
    record_image_digest("frigate", "sha256:bbb", generated_dir=generated_dir)  # change 1

    monkeypatch.setattr(history_module, "datetime", _frozen_at(_at(11)))
    record_package_inventory("frigate", "dpkg", PACKAGES_TWO, generated_dir=generated_dir)

    monkeypatch.setattr(history_module, "datetime", _frozen_at(_at(12)))
    record_image_digest("frigate", "sha256:ccc", generated_dir=generated_dir)  # change 2

    monkeypatch.setattr(history_module, "datetime", _frozen_at(_at(13)))
    record_package_inventory("frigate", "dpkg", PACKAGES_THREE, generated_dir=generated_dir)

    store = OxigraphGraphStore(tmp_path / "graph")
    summary = project_upgrade_correlation(store, generated_dir=generated_dir)

    assert summary.digest_changes_seen == 2
    assert summary.correlations_written == 2

    links = {
        (row["s"], row["o"])
        for row in store.query(
            f"SELECT ?s ?o WHERE {{ ?s <{AISTACK_UPGRADE_CORRELATES_WITH}> ?o }}"
        )
    }
    expected_first = (
        docker_packages_iri("frigate", format_instant(_at(9))),
        docker_packages_iri("frigate", format_instant(_at(11))),
    )
    expected_second = (
        docker_packages_iri("frigate", format_instant(_at(11))),
        docker_packages_iri("frigate", format_instant(_at(13))),
    )
    assert links == {expected_first, expected_second}


def test_a_digest_change_with_no_packages_before_it_is_not_correlated(
    tmp_path: Path, monkeypatch
):
    generated_dir = tmp_path / "reports" / "generated"

    monkeypatch.setattr(history_module, "datetime", _frozen_at(_at(8)))
    record_image_digest("frigate", "sha256:aaa", generated_dir=generated_dir)

    monkeypatch.setattr(history_module, "datetime", _frozen_at(_at(9)))
    record_image_digest("frigate", "sha256:bbb", generated_dir=generated_dir)  # change, no packages yet

    monkeypatch.setattr(history_module, "datetime", _frozen_at(_at(10)))
    record_package_inventory("frigate", "dpkg", PACKAGES_ONE, generated_dir=generated_dir)

    store = OxigraphGraphStore(tmp_path / "graph")
    summary = project_upgrade_correlation(store, generated_dir=generated_dir)

    assert summary.subjects_seen == 1
    assert summary.digest_changes_seen == 1
    assert summary.correlations_written == 0


def test_a_digest_change_with_no_packages_after_it_is_not_correlated(
    tmp_path: Path, monkeypatch
):
    generated_dir = tmp_path / "reports" / "generated"

    monkeypatch.setattr(history_module, "datetime", _frozen_at(_at(8)))
    record_image_digest("frigate", "sha256:aaa", generated_dir=generated_dir)

    monkeypatch.setattr(history_module, "datetime", _frozen_at(_at(9)))
    record_package_inventory("frigate", "dpkg", PACKAGES_ONE, generated_dir=generated_dir)

    monkeypatch.setattr(history_module, "datetime", _frozen_at(_at(10)))
    record_image_digest("frigate", "sha256:bbb", generated_dir=generated_dir)  # change, no packages after

    store = OxigraphGraphStore(tmp_path / "graph")
    summary = project_upgrade_correlation(store, generated_dir=generated_dir)

    assert summary.subjects_seen == 1
    assert summary.digest_changes_seen == 1
    assert summary.correlations_written == 0


def test_a_subject_with_digest_history_but_no_packages_history_is_skipped_entirely(
    tmp_path: Path, monkeypatch
):
    generated_dir = tmp_path / "reports" / "generated"

    monkeypatch.setattr(history_module, "datetime", _frozen_at(_at(8)))
    record_image_digest("no-packages", "sha256:aaa", generated_dir=generated_dir)
    monkeypatch.setattr(history_module, "datetime", _frozen_at(_at(9)))
    record_image_digest("no-packages", "sha256:bbb", generated_dir=generated_dir)

    monkeypatch.setattr(history_module, "datetime", _frozen_at(_at(10)))
    record_package_inventory("has-both", "dpkg", PACKAGES_ONE, generated_dir=generated_dir)

    store = OxigraphGraphStore(tmp_path / "graph")
    summary = project_upgrade_correlation(store, generated_dir=generated_dir)

    # "has-both" never got its own digest history, "no-packages" never
    # got its own packages history — neither subject appears in both
    # roots, so neither is even attempted.
    assert summary.subjects_seen == 0
    assert summary.correlations_written == 0


def test_a_subject_whose_name_embeds_a_slash_is_correctly_correlated(
    tmp_path: Path, monkeypatch
):
    generated_dir = tmp_path / "reports" / "generated"

    monkeypatch.setattr(history_module, "datetime", _frozen_at(_at(8)))
    record_image_digest("arrstack/gluetun", "sha256:aaa", generated_dir=generated_dir)

    monkeypatch.setattr(history_module, "datetime", _frozen_at(_at(9)))
    record_package_inventory(
        "arrstack/gluetun", "dpkg", PACKAGES_ONE, generated_dir=generated_dir
    )

    monkeypatch.setattr(history_module, "datetime", _frozen_at(_at(10)))
    record_image_digest("arrstack/gluetun", "sha256:bbb", generated_dir=generated_dir)

    monkeypatch.setattr(history_module, "datetime", _frozen_at(_at(11)))
    record_package_inventory(
        "arrstack/gluetun", "dpkg", PACKAGES_TWO, generated_dir=generated_dir
    )

    store = OxigraphGraphStore(tmp_path / "graph")
    summary = project_upgrade_correlation(store, generated_dir=generated_dir)

    assert summary.correlations_written == 1
