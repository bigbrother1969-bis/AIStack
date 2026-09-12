from pathlib import Path

import pytest

from aistack.network_discovery.definition import NetworkDiscoveryDefinition
from aistack.network_discovery.yaml import (
    load_network_discovery_yaml,
    save_network_discovery_yaml,
)


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


# --------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------


def test_the_required_fields_are_loaded(tmp_path: Path):
    path = write(
        tmp_path / "network_discovery.yml",
        """
        cidr: 192.168.1.0/24
        ssh_key_path_env: AISTACK_NETWORK_SSH_KEY_PATH
        """,
    )

    definition = load_network_discovery_yaml(path)
    assert definition.cidr == "192.168.1.0/24"
    assert definition.ssh_key_path_env == "AISTACK_NETWORK_SSH_KEY_PATH"


def test_ssh_usernames_are_loaded_in_order(tmp_path: Path):
    path = write(
        tmp_path / "network_discovery.yml",
        """
        cidr: 192.168.1.0/24
        ssh_key_path_env: AISTACK_NETWORK_SSH_KEY_PATH
        ssh_usernames:
          - pi
          - pi-hole
        """,
    )

    assert load_network_discovery_yaml(path).ssh_usernames == ("pi", "pi-hole")


def test_ssh_usernames_default_to_empty_when_absent(tmp_path: Path):
    path = write(
        tmp_path / "network_discovery.yml",
        """
        cidr: 192.168.1.0/24
        ssh_key_path_env: AISTACK_NETWORK_SSH_KEY_PATH
        """,
    )

    assert load_network_discovery_yaml(path).ssh_usernames == ()


def test_ssh_timeout_seconds_defaults_to_three(tmp_path: Path):
    path = write(
        tmp_path / "network_discovery.yml",
        """
        cidr: 192.168.1.0/24
        ssh_key_path_env: AISTACK_NETWORK_SSH_KEY_PATH
        """,
    )

    assert load_network_discovery_yaml(path).ssh_timeout_seconds == 3.0


def test_ssh_timeout_seconds_is_read_when_declared(tmp_path: Path):
    path = write(
        tmp_path / "network_discovery.yml",
        """
        cidr: 192.168.1.0/24
        ssh_key_path_env: AISTACK_NETWORK_SSH_KEY_PATH
        ssh_timeout_seconds: 5
        """,
    )

    assert load_network_discovery_yaml(path).ssh_timeout_seconds == 5.0


# --------------------------------------------------------------------
# Malformed input
# --------------------------------------------------------------------


def test_a_missing_cidr_is_named(tmp_path: Path):
    path = write(
        tmp_path / "network_discovery.yml",
        "ssh_key_path_env: AISTACK_NETWORK_SSH_KEY_PATH\n",
    )

    with pytest.raises(ValueError, match="cidr"):
        load_network_discovery_yaml(path)


def test_a_missing_ssh_key_path_env_is_named(tmp_path: Path):
    path = write(tmp_path / "network_discovery.yml", "cidr: 192.168.1.0/24\n")

    with pytest.raises(ValueError, match="ssh_key_path_env"):
        load_network_discovery_yaml(path)


def test_ssh_usernames_that_is_not_a_list_is_refused(tmp_path: Path):
    path = write(
        tmp_path / "network_discovery.yml",
        """
        cidr: 192.168.1.0/24
        ssh_key_path_env: AISTACK_NETWORK_SSH_KEY_PATH
        ssh_usernames: pi
        """,
    )

    with pytest.raises(ValueError, match="ssh_usernames must be a list"):
        load_network_discovery_yaml(path)


def test_a_file_that_is_not_a_mapping_is_refused(tmp_path: Path):
    path = write(tmp_path / "network_discovery.yml", "- one\n- two\n")

    with pytest.raises(ValueError, match="mapping"):
        load_network_discovery_yaml(path)


# --------------------------------------------------------------------
# Saving — round-trips through load
# --------------------------------------------------------------------


def test_a_saved_definition_loads_back_identically(tmp_path: Path):
    definition = NetworkDiscoveryDefinition(
        cidr="192.168.1.0/24",
        ssh_key_path_env="AISTACK_NETWORK_SSH_KEY_PATH",
        ssh_usernames=("pi", "pi-hole"),
        ssh_timeout_seconds=3.0,
    )
    path = tmp_path / "network_discovery.yml"

    save_network_discovery_yaml(definition, path)

    assert load_network_discovery_yaml(path) == definition


def test_saving_creates_missing_parent_directories(tmp_path: Path):
    definition = NetworkDiscoveryDefinition(
        cidr="192.168.1.0/24", ssh_key_path_env="AISTACK_NETWORK_SSH_KEY_PATH"
    )
    path = tmp_path / "nested" / "dir" / "network_discovery.yml"

    save_network_discovery_yaml(definition, path)

    assert path.exists()


def test_a_username_containing_a_yaml_special_character_round_trips(tmp_path: Path):
    definition = NetworkDiscoveryDefinition(
        cidr="192.168.1.0/24",
        ssh_key_path_env="AISTACK_NETWORK_SSH_KEY_PATH",
        ssh_usernames=("a: b", "- weird"),
    )
    path = tmp_path / "network_discovery.yml"

    save_network_discovery_yaml(definition, path)

    assert load_network_discovery_yaml(path).ssh_usernames == ("a: b", "- weird")


def test_an_empty_username_list_saves_and_reloads_as_empty(tmp_path: Path):
    definition = NetworkDiscoveryDefinition(
        cidr="192.168.1.0/24", ssh_key_path_env="AISTACK_NETWORK_SSH_KEY_PATH"
    )
    path = tmp_path / "network_discovery.yml"

    save_network_discovery_yaml(definition, path)

    assert load_network_discovery_yaml(path).ssh_usernames == ()


# --------------------------------------------------------------------
# Dataclass defaults
# --------------------------------------------------------------------


def test_dataclass_defaults_when_built_directly():
    definition = NetworkDiscoveryDefinition(
        cidr="192.168.1.0/24", ssh_key_path_env="AISTACK_NETWORK_SSH_KEY_PATH"
    )
    assert definition.ssh_usernames == ()
    assert definition.ssh_timeout_seconds == 3.0


# --------------------------------------------------------------------
# The real, shipped file
# --------------------------------------------------------------------


def test_the_real_network_discovery_definition_loads():
    """
    `src/aistack/network_discovery/definitions/network_discovery.yml`
    is not a fixture — it is the real, hand-maintained definition
    `aistack.cli.network_docker_discover` reads. A typo or a dropped
    field in the real file is caught here, the same discipline
    `test_the_real_infrastructure_topology_loads` already applies.
    """

    repo_root = Path(__file__).resolve().parents[3]

    definition = load_network_discovery_yaml(
        repo_root
        / "src"
        / "aistack"
        / "network_discovery"
        / "definitions"
        / "network_discovery.yml"
    )

    assert definition.cidr == "192.168.1.0/24"
    assert definition.ssh_key_path_env == "AISTACK_NETWORK_SSH_KEY_PATH"
    assert definition.ssh_usernames == ("pi", "pi-hole")
    assert definition.ssh_timeout_seconds == 3.0
