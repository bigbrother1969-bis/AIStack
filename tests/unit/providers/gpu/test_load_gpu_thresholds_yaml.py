from pathlib import Path

import pytest

from aistack.contracts.gpu_threshold import (
    MEMORY_PERCENT,
    TEMPERATURE_CELSIUS,
    UTILIZATION_PERCENT,
)
from aistack.providers.gpu.yaml import load_gpu_thresholds_yaml


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_a_complete_definition_is_loaded(tmp_path: Path):
    path = write(
        tmp_path / "gpu_thresholds.yml",
        """
        hosts:
          - host: GIGABYTE
            thresholds:
              - kind: temperature_celsius
                celsius: 80
              - kind: utilization_percent
                percent: 90
              - kind: memory_percent
                percent: 90
        """,
    )

    register = load_gpu_thresholds_yaml(path)

    assert len(register.hosts) == 1
    gigabyte = register.hosts[0]

    assert gigabyte.host == "GIGABYTE"
    assert len(gigabyte.thresholds) == 3

    by_kind = {t.kind: t.value for t in gigabyte.thresholds}
    assert by_kind[TEMPERATURE_CELSIUS] == 80.0
    assert by_kind[UTILIZATION_PERCENT] == 90.0
    assert by_kind[MEMORY_PERCENT] == 90.0


def test_a_host_with_no_thresholds_yet_is_valid(tmp_path: Path):
    path = write(
        tmp_path / "no_thresholds.yml",
        """
        hosts:
          - host: GIGABYTE
            thresholds: []
        """,
    )

    register = load_gpu_thresholds_yaml(path)

    assert register.hosts[0].thresholds == ()


def test_a_definition_with_no_hosts_is_valid(tmp_path: Path):
    path = write(tmp_path / "no_hosts.yml", "hosts: []\n")

    assert load_gpu_thresholds_yaml(path).hosts == ()


def test_a_missing_hosts_key_is_named(tmp_path: Path):
    path = write(tmp_path / "no_key.yml", "not_hosts: []\n")

    with pytest.raises(ValueError, match="missing: hosts"):
        load_gpu_thresholds_yaml(path)


def test_hosts_that_are_not_a_list_are_refused(tmp_path: Path):
    path = write(tmp_path / "not_a_list.yml", "hosts: GIGABYTE\n")

    with pytest.raises(ValueError, match="hosts must be a list"):
        load_gpu_thresholds_yaml(path)


def test_a_host_missing_its_own_required_field_is_named(tmp_path: Path):
    path = write(
        tmp_path / "bad_host.yml",
        """
        hosts:
          - thresholds: []
        """,
    )

    with pytest.raises(ValueError, match=r"hosts\[0\].*host"):
        load_gpu_thresholds_yaml(path)


def test_a_hosts_thresholds_that_are_not_a_list_are_refused(tmp_path: Path):
    path = write(
        tmp_path / "not_a_list_thresholds.yml",
        """
        hosts:
          - host: GIGABYTE
            thresholds: /
        """,
    )

    with pytest.raises(ValueError, match="thresholds must be a list"):
        load_gpu_thresholds_yaml(path)


def test_a_threshold_with_an_unknown_kind_is_refused(tmp_path: Path):
    path = write(
        tmp_path / "unknown_kind.yml",
        """
        hosts:
          - host: GIGABYTE
            thresholds:
              - kind: power_watts
                value: 50
        """,
    )

    with pytest.raises(ValueError, match="unknown threshold kind"):
        load_gpu_thresholds_yaml(path)


def test_a_temperature_threshold_missing_celsius_is_named(tmp_path: Path):
    path = write(
        tmp_path / "no_celsius.yml",
        """
        hosts:
          - host: GIGABYTE
            thresholds:
              - kind: temperature_celsius
        """,
    )

    with pytest.raises(ValueError, match=r"hosts\[0\]\.thresholds\[0\].*celsius"):
        load_gpu_thresholds_yaml(path)


def test_a_utilization_threshold_missing_percent_is_named(tmp_path: Path):
    path = write(
        tmp_path / "no_percent.yml",
        """
        hosts:
          - host: GIGABYTE
            thresholds:
              - kind: utilization_percent
        """,
    )

    with pytest.raises(ValueError, match=r"hosts\[0\]\.thresholds\[0\].*percent"):
        load_gpu_thresholds_yaml(path)


def test_a_threshold_missing_its_kind_is_named(tmp_path: Path):
    path = write(
        tmp_path / "no_kind.yml",
        """
        hosts:
          - host: GIGABYTE
            thresholds:
              - celsius: 80
        """,
    )

    with pytest.raises(ValueError, match=r"hosts\[0\]\.thresholds\[0\].*kind"):
        load_gpu_thresholds_yaml(path)


def test_a_definition_that_is_not_a_mapping_is_refused(tmp_path: Path):
    path = write(tmp_path / "list.yml", "- one\n- two\n")

    with pytest.raises(ValueError, match="mapping"):
        load_gpu_thresholds_yaml(path)


def test_the_real_gpu_thresholds_definition_loads():
    """
    `src/aistack/providers/gpu/definitions/gpu_thresholds.yml` is not a
    fixture — it is `OPS-0007`'s own declared values, the file both
    `aistack.cli.runtime_diagnose` and `aistack.cli.health_render`
    actually read. Loading it here means a typo in the real,
    hand-written file is caught by the test suite, the same discipline
    `test_the_real_backup_thresholds_definition_loads` already holds.
    """

    repo_root = Path(__file__).resolve().parents[4]

    register = load_gpu_thresholds_yaml(
        repo_root / "src" / "aistack" / "providers" / "gpu" / "definitions" / "gpu_thresholds.yml"
    )

    gigabyte = register.for_host("GIGABYTE")

    assert len(gigabyte) == 3
    by_kind = {t.kind: t.value for t in gigabyte}
    assert by_kind[TEMPERATURE_CELSIUS] == 80.0
    assert by_kind[UTILIZATION_PERCENT] == 90.0
    assert by_kind[MEMORY_PERCENT] == 90.0

    # Case-sensitive on purpose, the same reason
    # `test_the_real_backup_thresholds_definition_loads` asserts it.
    assert register.for_host("gigabyte") == ()
    assert register.for_host("raspberry") == ()


def test_invalid_yaml_syntax_is_reported_as_a_value_error(tmp_path: Path):
    path = write(tmp_path / "broken.yml", "hosts: [not, valid,\n")

    with pytest.raises(ValueError, match="not valid YAML"):
        load_gpu_thresholds_yaml(path)
