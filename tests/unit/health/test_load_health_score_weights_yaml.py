from pathlib import Path

import pytest

from aistack.health.yaml import load_health_score_weights_yaml


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_a_complete_definition_is_loaded(tmp_path: Path):
    path = write(
        tmp_path / "health_score_weights.yml",
        """
        weights:
          - domain: Stockage
            points: 10
          - domain: Services
            points: 15
        """,
    )

    weights = load_health_score_weights_yaml(path)

    assert len(weights.weights) == 2
    assert weights.for_domain("Stockage") == 10
    assert weights.for_domain("Services") == 15


def test_a_definition_missing_the_weights_key_is_refused(tmp_path: Path):
    path = write(tmp_path / "empty.yml", "not_weights: []\n")

    with pytest.raises(ValueError, match="missing: weights"):
        load_health_score_weights_yaml(path)


def test_weights_that_is_not_a_list_is_refused(tmp_path: Path):
    path = write(tmp_path / "bad.yml", "weights: not-a-list\n")

    with pytest.raises(ValueError, match="must be a list"):
        load_health_score_weights_yaml(path)


def test_an_entry_that_is_not_a_mapping_is_refused(tmp_path: Path):
    path = write(tmp_path / "bad.yml", "weights:\n  - just-a-string\n")

    with pytest.raises(ValueError, match="must be a mapping"):
        load_health_score_weights_yaml(path)


def test_an_entry_missing_domain_is_refused(tmp_path: Path):
    path = write(tmp_path / "bad.yml", "weights:\n  - points: 10\n")

    with pytest.raises(ValueError, match="missing: domain"):
        load_health_score_weights_yaml(path)


def test_an_entry_missing_points_is_refused(tmp_path: Path):
    path = write(tmp_path / "bad.yml", "weights:\n  - domain: Stockage\n")

    with pytest.raises(ValueError, match="missing: points"):
        load_health_score_weights_yaml(path)


def test_a_definition_that_is_not_a_mapping_is_refused(tmp_path: Path):
    path = write(tmp_path / "list.yml", "- one\n- two\n")

    with pytest.raises(ValueError, match="mapping"):
        load_health_score_weights_yaml(path)


def test_invalid_yaml_syntax_is_reported_as_a_value_error(tmp_path: Path):
    path = write(tmp_path / "broken.yml", "weights: [not, valid,\n")

    with pytest.raises(ValueError, match="not valid YAML"):
        load_health_score_weights_yaml(path)


def test_the_real_health_score_weights_definition_loads():
    """
    `src/aistack/health/definitions/health_score_weights.yml` is not a
    fixture — it is `OPS-0008`'s own declared values, the file
    `aistack.cli.health_render` actually reads. Loading it here means a
    typo in the real, hand-written file is caught by the test suite,
    the same discipline `test_the_real_gpu_thresholds_definition_loads`
    already holds.
    """

    repo_root = Path(__file__).resolve().parents[3]

    weights = load_health_score_weights_yaml(
        repo_root
        / "src"
        / "aistack"
        / "health"
        / "definitions"
        / "health_score_weights.yml"
    )

    assert weights.for_domain("Stockage") == 10
    assert weights.for_domain("Services") == 15
    assert weights.for_domain("Sauvegarde / PRA") == 25
    assert weights.for_domain("GPU") == 8

    # Every domain PLAN-J7 names has a declared weight — the closed-set
    # discipline `OPS-0008` § *No weight for a domain outside this
    # closed set* states.
    assert weights.for_domain("Raspberry") is None
