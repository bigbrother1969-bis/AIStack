from pathlib import Path

import pytest

from aistack.architecture.cmdb_definition import CmdbProbeTargetDefinition
from aistack.architecture.yaml import load_cmdb_probe_targets_yaml


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


# --------------------------------------------------------------------
# Targets
# --------------------------------------------------------------------


def test_a_target_is_loaded(tmp_path: Path):
    path = write(
        tmp_path / "cmdb.yml",
        """
        targets:
          - name: Gitea
            url: https://gitea.persiaut-family.fr
        """,
    )

    target = load_cmdb_probe_targets_yaml(path)[0]
    assert target.name == "Gitea"
    assert target.url == "https://gitea.persiaut-family.fr"


def test_a_target_missing_its_name_is_named_by_position(tmp_path: Path):
    path = write(
        tmp_path / "cmdb.yml",
        """
        targets:
          - url: https://gitea.persiaut-family.fr
        """,
    )

    with pytest.raises(ValueError, match=r"targets\[0\].*name"):
        load_cmdb_probe_targets_yaml(path)


def test_a_target_missing_its_url_is_named_by_position(tmp_path: Path):
    path = write(
        tmp_path / "cmdb.yml",
        """
        targets:
          - name: Gitea
        """,
    )

    with pytest.raises(ValueError, match=r"targets\[0\].*url"):
        load_cmdb_probe_targets_yaml(path)


def test_a_target_that_is_not_a_mapping_is_refused(tmp_path: Path):
    path = write(
        tmp_path / "cmdb.yml",
        """
        targets:
          - Gitea
        """,
    )

    with pytest.raises(ValueError, match=r"targets\[0\] must be a mapping"):
        load_cmdb_probe_targets_yaml(path)


def test_order_is_preserved_from_the_source_file(tmp_path: Path):
    path = write(
        tmp_path / "cmdb.yml",
        """
        targets:
          - name: Gitea
            url: https://gitea.persiaut-family.fr
          - name: Vaultwarden
            url: https://vault.persiaut-family.fr
        """,
    )

    targets = load_cmdb_probe_targets_yaml(path)
    assert [t.name for t in targets] == ["Gitea", "Vaultwarden"]


# --------------------------------------------------------------------
# Whole-file shape
# --------------------------------------------------------------------


def test_a_missing_targets_key_defaults_to_empty(tmp_path: Path):
    path = write(tmp_path / "cmdb.yml", "other_key: []\n")

    assert load_cmdb_probe_targets_yaml(path) == ()


def test_a_completely_empty_file_is_valid(tmp_path: Path):
    path = write(tmp_path / "cmdb.yml", "")

    assert load_cmdb_probe_targets_yaml(path) == ()


def test_targets_that_is_not_a_list_is_refused(tmp_path: Path):
    path = write(tmp_path / "cmdb.yml", "targets: Gitea\n")

    with pytest.raises(ValueError, match="targets must be a list"):
        load_cmdb_probe_targets_yaml(path)


def test_a_file_that_is_not_a_mapping_is_refused(tmp_path: Path):
    path = write(tmp_path / "cmdb.yml", "- one\n- two\n")

    with pytest.raises(ValueError, match="mapping"):
        load_cmdb_probe_targets_yaml(path)


def test_the_dataclass_takes_name_and_url():
    target = CmdbProbeTargetDefinition(name="Gitea", url="https://gitea.persiaut-family.fr")
    assert target.name == "Gitea"
    assert target.url == "https://gitea.persiaut-family.fr"


# --------------------------------------------------------------------
# The real, shipped file
# --------------------------------------------------------------------


def test_the_real_cmdb_probe_targets_load():
    """
    `src/aistack/architecture/definitions/cmdb_probe_targets.yml` is
    not a fixture — it is the real, hand-maintained target list
    `architecture_render.py` reads. A typo or a dropped field in the
    real file is caught here, the same discipline
    `test_the_real_infrastructure_topology_loads` already applies.
    """

    repo_root = Path(__file__).resolve().parents[3]

    targets = load_cmdb_probe_targets_yaml(
        repo_root
        / "src"
        / "aistack"
        / "architecture"
        / "definitions"
        / "cmdb_probe_targets.yml"
    )

    assert len(targets) == 46

    names = [target.name for target in targets]
    assert len(names) == len(set(names)), "every target name should be unique"

    for target in targets:
        assert target.name
        assert target.url.startswith("https://")

    by_name = {target.name: target for target in targets}
    assert "AIStack Console" not in by_name
    assert by_name["FreeboxOS"].url == "https://persiaut-family.fr:15277/"
    assert by_name["Indy"].url == "https://app.indy.fr/"
    assert by_name["Gitea"].url == "https://gitea.persiaut-family.fr"
