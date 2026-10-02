from pathlib import Path

import pytest

from aistack.contracts.instance_config import InstanceConfig
from aistack.instance.yaml import load_instance_config_yaml


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_a_complete_definition_is_loaded(tmp_path: Path):
    path = write(
        tmp_path / "instance_config.yml",
        """
        lan_hostname: GIGABYTE
        service_ports:
          console: 8183
          selection_ui: 8181
        """,
    )

    config = load_instance_config_yaml(path)

    assert config == InstanceConfig(
        lan_hostname="GIGABYTE",
        service_ports={"console": 8183, "selection_ui": 8181},
    )


def test_a_definition_missing_lan_hostname_is_refused(tmp_path: Path):
    path = write(
        tmp_path / "bad.yml", "service_ports:\n  console: 8183\n"
    )

    with pytest.raises(ValueError, match="missing: lan_hostname"):
        load_instance_config_yaml(path)


def test_a_definition_missing_service_ports_is_refused(tmp_path: Path):
    path = write(tmp_path / "bad.yml", "lan_hostname: GIGABYTE\n")

    with pytest.raises(ValueError, match="missing: service_ports"):
        load_instance_config_yaml(path)


def test_service_ports_that_is_not_a_mapping_is_refused(tmp_path: Path):
    path = write(
        tmp_path / "bad.yml",
        "lan_hostname: GIGABYTE\nservice_ports: not-a-mapping\n",
    )

    with pytest.raises(ValueError, match="service_ports must be a mapping"):
        load_instance_config_yaml(path)


def test_a_definition_that_is_not_a_mapping_is_refused(tmp_path: Path):
    path = write(tmp_path / "list.yml", "- one\n- two\n")

    with pytest.raises(ValueError, match="must contain a mapping"):
        load_instance_config_yaml(path)


def test_invalid_yaml_syntax_is_reported_as_a_value_error(tmp_path: Path):
    path = write(tmp_path / "broken.yml", "lan_hostname: [not, valid,\n")

    with pytest.raises(ValueError, match="not valid YAML"):
        load_instance_config_yaml(path)


def test_the_real_instance_config_definition_loads():
    """
    `src/aistack/instance/definitions/instance_config.yml` is not a
    fixture — it is AIStack's own real, declared address (R10,
    cadré 2026-09-30). Loading it here catches a typo in the real,
    hand-written file, the same discipline
    `test_the_real_console_links_definition_loads` already holds.
    """

    repo_root = Path(__file__).resolve().parents[3]

    config = load_instance_config_yaml(
        repo_root
        / "src"
        / "aistack"
        / "instance"
        / "definitions"
        / "instance_config.yml"
    )

    assert config.lan_hostname == "GIGABYTE"
    assert config.service_ports == {
        "selection_ui": 8181,
        "priority_ui": 8182,
        "console": 8183,
        "network_discovery_ui": 8184,
        "troubleshooting_assistant_ui": 8185,
        "timemachine_ui": 8186,
        "web_lan": 8187,
    }
    assert config.service_url("console") == "http://GIGABYTE:8183"
