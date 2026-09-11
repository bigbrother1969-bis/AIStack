from pathlib import Path

import pytest

from aistack.providers.filesystem.yaml import load_backup_thresholds_yaml


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_a_complete_definition_is_loaded(tmp_path: Path):
    path = write(
        tmp_path / "backup_thresholds.yml",
        """
        hosts:
          - host: GIGABYTE
            thresholds:
              - path: /media/BACKUP/persiaut-consulting/wordpress/
                max_age_days: 7
        """,
    )

    register = load_backup_thresholds_yaml(path)

    assert len(register.hosts) == 1
    gigabyte = register.hosts[0]

    assert gigabyte.host == "GIGABYTE"
    assert len(gigabyte.thresholds) == 1

    wordpress = gigabyte.thresholds[0]
    assert wordpress.path == "/media/BACKUP/persiaut-consulting/wordpress/"
    assert wordpress.max_age_hours == 7 * 24


def test_a_host_with_no_thresholds_yet_is_valid(tmp_path: Path):
    path = write(
        tmp_path / "no_thresholds.yml",
        """
        hosts:
          - host: GIGABYTE
            thresholds: []
        """,
    )

    register = load_backup_thresholds_yaml(path)

    assert register.hosts[0].thresholds == ()


def test_a_definition_with_no_hosts_is_valid(tmp_path: Path):
    path = write(tmp_path / "no_hosts.yml", "hosts: []\n")

    assert load_backup_thresholds_yaml(path).hosts == ()


def test_a_missing_hosts_key_is_named(tmp_path: Path):
    path = write(tmp_path / "no_key.yml", "not_hosts: []\n")

    with pytest.raises(ValueError, match="missing: hosts"):
        load_backup_thresholds_yaml(path)


def test_hosts_that_are_not_a_list_are_refused(tmp_path: Path):
    path = write(tmp_path / "not_a_list.yml", "hosts: GIGABYTE\n")

    with pytest.raises(ValueError, match="hosts must be a list"):
        load_backup_thresholds_yaml(path)


def test_a_host_missing_its_own_required_field_is_named(tmp_path: Path):
    path = write(
        tmp_path / "bad_host.yml",
        """
        hosts:
          - thresholds: []
        """,
    )

    with pytest.raises(ValueError, match=r"hosts\[0\].*host"):
        load_backup_thresholds_yaml(path)


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
        load_backup_thresholds_yaml(path)


def test_a_threshold_missing_its_max_age_days_is_named(tmp_path: Path):
    path = write(
        tmp_path / "no_max_age.yml",
        """
        hosts:
          - host: GIGABYTE
            thresholds:
              - path: /media/BACKUP/wordpress/
        """,
    )

    with pytest.raises(ValueError, match=r"hosts\[0\]\.thresholds\[0\].*max_age_days"):
        load_backup_thresholds_yaml(path)


def test_a_threshold_missing_its_path_is_named(tmp_path: Path):
    path = write(
        tmp_path / "no_path.yml",
        """
        hosts:
          - host: GIGABYTE
            thresholds:
              - max_age_days: 7
        """,
    )

    with pytest.raises(ValueError, match=r"hosts\[0\]\.thresholds\[0\].*path"):
        load_backup_thresholds_yaml(path)


def test_a_definition_that_is_not_a_mapping_is_refused(tmp_path: Path):
    path = write(tmp_path / "list.yml", "- one\n- two\n")

    with pytest.raises(ValueError, match="mapping"):
        load_backup_thresholds_yaml(path)


def test_the_real_backup_thresholds_definition_loads():
    """
    `src/aistack/providers/filesystem/definitions/backup_thresholds.yml`
    is not a fixture — it is `OPS-0006`'s own declared values, the
    file both `aistack.cli.runtime_diagnose` and `aistack.cli
    .health_render` actually read. Loading it here means a typo in the
    real, hand-written file is caught by the test suite, the same
    discipline `test_the_real_storage_thresholds_definition_loads`
    already holds.
    """

    repo_root = Path(__file__).resolve().parents[4]

    register = load_backup_thresholds_yaml(
        repo_root
        / "src"
        / "aistack"
        / "providers"
        / "filesystem"
        / "definitions"
        / "backup_thresholds.yml"
    )

    gigabyte = register.for_host("GIGABYTE")

    assert len(gigabyte) == 1
    wordpress = gigabyte[0]
    assert wordpress.path == "/media/BACKUP/persiaut-consulting/wordpress/"
    assert wordpress.max_age_hours == 7 * 24

    # Case-sensitive on purpose, the same reason
    # `test_the_real_storage_thresholds_definition_loads` asserts it.
    assert register.for_host("gigabyte") == ()
    assert register.for_host("raspberry") == ()


def test_invalid_yaml_syntax_is_reported_as_a_value_error(tmp_path: Path):
    path = write(tmp_path / "broken.yml", "hosts: [not, valid,\n")

    with pytest.raises(ValueError, match="not valid YAML"):
        load_backup_thresholds_yaml(path)
