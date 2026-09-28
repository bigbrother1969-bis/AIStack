from __future__ import annotations

import json
from pathlib import Path

from aistack.providers.docker.diff_history import has_changed, record_docker_diff

ONE_CHANGE = [{"kind": "A", "path": "/run/nginx.pid"}]
TWO_CHANGES = [
    {"kind": "A", "path": "/run/nginx.pid"},
    {"kind": "C", "path": "/etc/hosts"},
]


def test_a_subject_s_first_observation_is_always_recorded_even_if_empty(tmp_path: Path):
    """
    No prior recording exists to compare against, so even an empty
    `changes` list is worth writing once — matching
    `aistack.generators.collection_gap.record_collection_gap`'s own
    restraint against inventing a comparison where none is possible.
    """
    generated_dir = tmp_path / "reports" / "generated"

    result = record_docker_diff("arrstack/gluetun", [], generated_dir=generated_dir)

    assert result is not None
    written = json.loads(result.read_text(encoding="utf-8"))
    assert written == {"subject": "arrstack/gluetun", "changes": []}


def test_an_identical_diff_is_not_recorded_again(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"
    record_docker_diff("arrstack/gluetun", ONE_CHANGE, generated_dir=generated_dir)

    second = record_docker_diff(
        "arrstack/gluetun", list(ONE_CHANGE), generated_dir=generated_dir
    )

    assert second is None


def test_a_changed_diff_is_recorded_and_replaces_the_latest_file(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"
    record_docker_diff("arrstack/gluetun", ONE_CHANGE, generated_dir=generated_dir)

    result = record_docker_diff(
        "arrstack/gluetun", TWO_CHANGES, generated_dir=generated_dir
    )

    assert result is not None
    written = json.loads(result.read_text(encoding="utf-8"))
    assert written["changes"] == TWO_CHANGES


def test_every_recorded_write_lands_in_history_too(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"
    record_docker_diff("arrstack/gluetun", ONE_CHANGE, generated_dir=generated_dir)
    record_docker_diff("arrstack/gluetun", TWO_CHANGES, generated_dir=generated_dir)

    history_dir = (
        generated_dir / "docker-diff" / "arrstack" / "gluetun" / "history" / "docker-diff"
    )
    assert len(list(history_dir.glob("*.json"))) == 2


def test_a_subject_embedding_a_slash_nests_a_directory_per_component(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"

    record_docker_diff("arrstack/gluetun", ONE_CHANGE, generated_dir=generated_dir)

    assert (
        generated_dir / "docker-diff" / "arrstack" / "gluetun" / "docker-diff.json"
    ).exists()


def test_two_different_subjects_do_not_collide(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"

    record_docker_diff("arrstack/gluetun", ONE_CHANGE, generated_dir=generated_dir)
    record_docker_diff("frigate", TWO_CHANGES, generated_dir=generated_dir)

    first = json.loads(
        (generated_dir / "docker-diff" / "arrstack" / "gluetun" / "docker-diff.json").read_text()
    )
    second = json.loads(
        (generated_dir / "docker-diff" / "frigate" / "docker-diff.json").read_text()
    )
    assert first["changes"] == ONE_CHANGE
    assert second["changes"] == TWO_CHANGES


# --- has_changed, the read-only half -------------------------------------


def test_has_changed_is_true_on_a_first_observation(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"
    assert has_changed("arrstack/gluetun", [], generated_dir=generated_dir) is True


def test_has_changed_reads_without_writing_anything(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"

    has_changed("arrstack/gluetun", ONE_CHANGE, generated_dir=generated_dir)

    assert not (generated_dir / "docker-diff").exists()


def test_has_changed_is_false_once_recorded_and_unchanged(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"
    record_docker_diff("arrstack/gluetun", ONE_CHANGE, generated_dir=generated_dir)

    assert (
        has_changed("arrstack/gluetun", list(ONE_CHANGE), generated_dir=generated_dir)
        is False
    )


def test_has_changed_is_true_once_the_value_actually_differs(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"
    record_docker_diff("arrstack/gluetun", ONE_CHANGE, generated_dir=generated_dir)

    assert (
        has_changed("arrstack/gluetun", TWO_CHANGES, generated_dir=generated_dir)
        is True
    )
