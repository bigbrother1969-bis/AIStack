from __future__ import annotations

import json
from pathlib import Path

from aistack.providers.docker.digest_history import has_changed, record_image_digest

DIGEST_ONE = "sha256:image-digest-1"
DIGEST_TWO = "sha256:image-digest-2"


def test_a_subject_s_first_observation_is_always_recorded(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"

    result = record_image_digest("arrstack/gluetun", DIGEST_ONE, generated_dir=generated_dir)

    assert result is not None
    written = json.loads(result.read_text(encoding="utf-8"))
    assert written == {"subject": "arrstack/gluetun", "digest": DIGEST_ONE}


def test_an_identical_digest_is_not_recorded_again(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"
    record_image_digest("arrstack/gluetun", DIGEST_ONE, generated_dir=generated_dir)

    second = record_image_digest("arrstack/gluetun", DIGEST_ONE, generated_dir=generated_dir)

    assert second is None


def test_a_changed_digest_is_recorded_and_replaces_the_latest_file(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"
    record_image_digest("arrstack/gluetun", DIGEST_ONE, generated_dir=generated_dir)

    result = record_image_digest("arrstack/gluetun", DIGEST_TWO, generated_dir=generated_dir)

    assert result is not None
    written = json.loads(result.read_text(encoding="utf-8"))
    assert written["digest"] == DIGEST_TWO


def test_every_recorded_write_lands_in_history_too(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"
    record_image_digest("arrstack/gluetun", DIGEST_ONE, generated_dir=generated_dir)
    record_image_digest("arrstack/gluetun", DIGEST_TWO, generated_dir=generated_dir)

    history_dir = (
        generated_dir / "docker-digest" / "arrstack" / "gluetun" / "history" / "docker-digest"
    )
    assert len(list(history_dir.glob("*.json"))) == 2


def test_a_subject_embedding_a_slash_nests_a_directory_per_component(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"

    record_image_digest("arrstack/gluetun", DIGEST_ONE, generated_dir=generated_dir)

    assert (
        generated_dir / "docker-digest" / "arrstack" / "gluetun" / "docker-digest.json"
    ).exists()


def test_two_different_subjects_do_not_collide(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"

    record_image_digest("arrstack/gluetun", DIGEST_ONE, generated_dir=generated_dir)
    record_image_digest("frigate", DIGEST_TWO, generated_dir=generated_dir)

    first = json.loads(
        (generated_dir / "docker-digest" / "arrstack" / "gluetun" / "docker-digest.json").read_text()
    )
    second = json.loads(
        (generated_dir / "docker-digest" / "frigate" / "docker-digest.json").read_text()
    )
    assert first["digest"] == DIGEST_ONE
    assert second["digest"] == DIGEST_TWO


# --- has_changed, the read-only half -------------------------------------


def test_has_changed_is_true_on_a_first_observation(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"
    assert has_changed("arrstack/gluetun", DIGEST_ONE, generated_dir=generated_dir) is True


def test_has_changed_reads_without_writing_anything(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"

    has_changed("arrstack/gluetun", DIGEST_ONE, generated_dir=generated_dir)

    assert not (generated_dir / "docker-digest").exists()


def test_has_changed_is_false_once_recorded_and_unchanged(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"
    record_image_digest("arrstack/gluetun", DIGEST_ONE, generated_dir=generated_dir)

    assert (
        has_changed("arrstack/gluetun", DIGEST_ONE, generated_dir=generated_dir) is False
    )


def test_has_changed_is_true_once_the_value_actually_differs(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"
    record_image_digest("arrstack/gluetun", DIGEST_ONE, generated_dir=generated_dir)

    assert (
        has_changed("arrstack/gluetun", DIGEST_TWO, generated_dir=generated_dir) is True
    )
