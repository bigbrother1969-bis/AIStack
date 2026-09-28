from __future__ import annotations

import json
from pathlib import Path

from aistack.providers.docker.packages_history import has_changed, record_package_inventory

PACKAGES_ONE = [{"name": "curl", "version": "7.88.1-10"}]
PACKAGES_TWO = [{"name": "curl", "version": "7.90.0-1"}]


def test_a_subject_s_first_observation_is_always_recorded(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"

    result = record_package_inventory(
        "arrstack/gluetun", "dpkg", PACKAGES_ONE, generated_dir=generated_dir
    )

    assert result is not None
    written = json.loads(result.read_text(encoding="utf-8"))
    assert written == {
        "subject": "arrstack/gluetun",
        "mechanism": "dpkg",
        "packages": PACKAGES_ONE,
    }


def test_an_identical_inventory_is_not_recorded_again(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"
    record_package_inventory("arrstack/gluetun", "dpkg", PACKAGES_ONE, generated_dir=generated_dir)

    second = record_package_inventory(
        "arrstack/gluetun", "dpkg", PACKAGES_ONE, generated_dir=generated_dir
    )

    assert second is None


def test_a_changed_package_list_is_recorded_and_replaces_the_latest_file(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"
    record_package_inventory("arrstack/gluetun", "dpkg", PACKAGES_ONE, generated_dir=generated_dir)

    result = record_package_inventory(
        "arrstack/gluetun", "dpkg", PACKAGES_TWO, generated_dir=generated_dir
    )

    assert result is not None
    written = json.loads(result.read_text(encoding="utf-8"))
    assert written["packages"] == PACKAGES_TWO


def test_a_mechanism_change_alone_is_recorded_even_with_the_same_empty_packages(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"
    record_package_inventory("frigate", "dpkg", [], generated_dir=generated_dir)

    result = record_package_inventory("frigate", "none", [], generated_dir=generated_dir)

    assert result is not None
    written = json.loads(result.read_text(encoding="utf-8"))
    assert written["mechanism"] == "none"


def test_every_recorded_write_lands_in_history_too(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"
    record_package_inventory("arrstack/gluetun", "dpkg", PACKAGES_ONE, generated_dir=generated_dir)
    record_package_inventory("arrstack/gluetun", "dpkg", PACKAGES_TWO, generated_dir=generated_dir)

    history_dir = (
        generated_dir
        / "docker-packages"
        / "arrstack"
        / "gluetun"
        / "history"
        / "docker-packages"
    )
    assert len(list(history_dir.glob("*.json"))) == 2


def test_a_subject_embedding_a_slash_nests_a_directory_per_component(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"

    record_package_inventory("arrstack/gluetun", "dpkg", PACKAGES_ONE, generated_dir=generated_dir)

    assert (
        generated_dir / "docker-packages" / "arrstack" / "gluetun" / "docker-packages.json"
    ).exists()


def test_two_different_subjects_do_not_collide(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"

    record_package_inventory("arrstack/gluetun", "dpkg", PACKAGES_ONE, generated_dir=generated_dir)
    record_package_inventory("frigate", "apk", PACKAGES_TWO, generated_dir=generated_dir)

    first = json.loads(
        (generated_dir / "docker-packages" / "arrstack" / "gluetun" / "docker-packages.json").read_text()
    )
    second = json.loads(
        (generated_dir / "docker-packages" / "frigate" / "docker-packages.json").read_text()
    )
    assert first["packages"] == PACKAGES_ONE
    assert second["packages"] == PACKAGES_TWO


# --- has_changed, the read-only half -------------------------------------


def test_has_changed_is_true_on_a_first_observation(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"
    assert has_changed("arrstack/gluetun", "dpkg", PACKAGES_ONE, generated_dir=generated_dir) is True


def test_has_changed_reads_without_writing_anything(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"

    has_changed("arrstack/gluetun", "dpkg", PACKAGES_ONE, generated_dir=generated_dir)

    assert not (generated_dir / "docker-packages").exists()


def test_has_changed_is_false_once_recorded_and_unchanged(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"
    record_package_inventory("arrstack/gluetun", "dpkg", PACKAGES_ONE, generated_dir=generated_dir)

    assert (
        has_changed("arrstack/gluetun", "dpkg", PACKAGES_ONE, generated_dir=generated_dir) is False
    )


def test_has_changed_is_true_once_the_value_actually_differs(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"
    record_package_inventory("arrstack/gluetun", "dpkg", PACKAGES_ONE, generated_dir=generated_dir)

    assert (
        has_changed("arrstack/gluetun", "dpkg", PACKAGES_TWO, generated_dir=generated_dir) is True
    )
