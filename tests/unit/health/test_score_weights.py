from __future__ import annotations

from pathlib import Path

from aistack.health.score_weights import health_score_weights


def test_a_missing_file_returns_none_with_a_note(tmp_path: Path):
    weights, note = health_score_weights(tmp_path / "does-not-exist.yml")

    assert weights is None
    assert "no health-score weight definition" in note


def test_an_unreadable_file_returns_none_with_a_note(tmp_path: Path):
    path = tmp_path / "weights.yml"
    path.write_text("not: [valid, yaml", encoding="utf-8")

    weights, note = health_score_weights(path)

    assert weights is None
    assert "not readable" in note


def test_a_valid_file_returns_the_weights_with_no_note(tmp_path: Path):
    path = tmp_path / "weights.yml"
    path.write_text(
        "weights:\n  - domain: Stockage\n    points: 10\n",
        encoding="utf-8",
    )

    weights, note = health_score_weights(path)

    assert weights is not None
    assert weights.for_domain("Stockage") == 10
    assert note == ""
