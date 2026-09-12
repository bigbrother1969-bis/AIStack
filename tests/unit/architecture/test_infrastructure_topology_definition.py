from pathlib import Path

import pytest

from aistack.architecture.topology_definition import (
    ExternalNodeDefinition,
    HardwareProfileDefinition,
    InfrastructureTopologyDefinition,
)
from aistack.architecture.yaml import load_infrastructure_topology_yaml


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


# --------------------------------------------------------------------
# External nodes
# --------------------------------------------------------------------


def test_an_external_node_is_loaded(tmp_path: Path):
    path = write(
        tmp_path / "topology.yml",
        """
        external_nodes:
          - name: OVH
            role: Registrar de noms de domaine
            description: Rien n'est hébergé chez OVH.
        """,
    )

    node = load_infrastructure_topology_yaml(path).external_nodes[0]
    assert node.name == "OVH"
    assert node.role == "Registrar de noms de domaine"
    assert node.description == "Rien n'est hébergé chez OVH."


def test_an_external_node_with_no_description_defaults_to_empty_string(
    tmp_path: Path,
):
    path = write(
        tmp_path / "topology.yml",
        """
        external_nodes:
          - name: Gmail
            role: Messagerie
        """,
    )

    node = load_infrastructure_topology_yaml(path).external_nodes[0]
    assert node.description == ""


def test_an_external_node_missing_its_name_is_named_by_position(tmp_path: Path):
    path = write(
        tmp_path / "topology.yml",
        """
        external_nodes:
          - role: Messagerie
        """,
    )

    with pytest.raises(ValueError, match=r"external_nodes\[0\].*name"):
        load_infrastructure_topology_yaml(path)


def test_an_external_node_missing_its_role_is_named_by_position(tmp_path: Path):
    path = write(
        tmp_path / "topology.yml",
        """
        external_nodes:
          - name: Gmail
        """,
    )

    with pytest.raises(ValueError, match=r"external_nodes\[0\].*role"):
        load_infrastructure_topology_yaml(path)


def test_an_external_node_that_is_not_a_mapping_is_refused(tmp_path: Path):
    path = write(
        tmp_path / "topology.yml",
        """
        external_nodes:
          - Gmail
        """,
    )

    with pytest.raises(ValueError, match=r"external_nodes\[0\] must be a mapping"):
        load_infrastructure_topology_yaml(path)


# --------------------------------------------------------------------
# Hardware
# --------------------------------------------------------------------


def test_a_hardware_profile_is_loaded(tmp_path: Path):
    path = write(
        tmp_path / "topology.yml",
        """
        hardware:
          - name: GIGABYTE
            model: Gigabyte GA-MA770T-UD3
            role: Hôte principal
            cpu: AMD Phenom(tm) II X4 945 Processor
            ram: 16 Go
            storage: 5 disques
            os: LMDE 7
            gpu: NVIDIA Quadro P400
        """,
    )

    profile = load_infrastructure_topology_yaml(path).hardware[0]
    assert profile.name == "GIGABYTE"
    assert profile.model == "Gigabyte GA-MA770T-UD3"
    assert profile.role == "Hôte principal"
    assert profile.cpu == "AMD Phenom(tm) II X4 945 Processor"
    assert profile.ram == "16 Go"
    assert profile.storage == "5 disques"
    assert profile.os_name == "LMDE 7"
    assert profile.gpu == "NVIDIA Quadro P400"


def test_a_hardware_profile_with_no_gpu_key_defaults_to_none(tmp_path: Path):
    path = write(
        tmp_path / "topology.yml",
        """
        hardware:
          - name: Raspberry Pi
            model: Raspberry Pi 3 Model B Rev 1.2
            role: Reverse proxy
            cpu: Broadcom BCM2837
            ram: 1 Go
            storage: Carte micro SD
            os: Debian (aarch64)
        """,
    )

    profile = load_infrastructure_topology_yaml(path).hardware[0]
    assert profile.gpu is None


def test_a_hardware_profile_with_a_blank_gpu_value_reads_as_none(tmp_path: Path):
    path = write(
        tmp_path / "topology.yml",
        """
        hardware:
          - name: Raspberry Pi
            model: Raspberry Pi 3 Model B Rev 1.2
            role: Reverse proxy
            cpu: Broadcom BCM2837
            ram: 1 Go
            storage: Carte micro SD
            os: Debian (aarch64)
            gpu:
        """,
    )

    profile = load_infrastructure_topology_yaml(path).hardware[0]
    assert profile.gpu is None


@pytest.mark.parametrize("missing_field", ["model", "role", "cpu", "ram", "storage", "os"])
def test_a_hardware_profile_missing_a_required_field_is_named(
    tmp_path: Path, missing_field: str
):
    fields = {
        "name": "GIGABYTE",
        "model": "Gigabyte GA-MA770T-UD3",
        "role": "Hôte principal",
        "cpu": "AMD Phenom(tm) II X4 945 Processor",
        "ram": "16 Go",
        "storage": "5 disques",
        "os": "LMDE 7",
    }
    del fields[missing_field]

    lines = "\n".join(f"            {key}: {value}" for key, value in fields.items())
    path = write(tmp_path / "topology.yml", f"hardware:\n          -\n{lines}\n")

    with pytest.raises(ValueError, match=rf"hardware\[0\].*{missing_field}"):
        load_infrastructure_topology_yaml(path)


def test_a_hardware_entry_that_is_not_a_mapping_is_refused(tmp_path: Path):
    path = write(
        tmp_path / "topology.yml",
        """
        hardware:
          - GIGABYTE
        """,
    )

    with pytest.raises(ValueError, match=r"hardware\[0\] must be a mapping"):
        load_infrastructure_topology_yaml(path)


# --------------------------------------------------------------------
# Whole-file shape
# --------------------------------------------------------------------


def test_both_top_level_keys_are_optional_and_default_to_empty(tmp_path: Path):
    path = write(tmp_path / "topology.yml", "external_nodes: []\n")

    definition = load_infrastructure_topology_yaml(path)
    assert definition.external_nodes == ()
    assert definition.hardware == ()


def test_a_completely_empty_file_is_valid(tmp_path: Path):
    path = write(tmp_path / "topology.yml", "")

    definition = load_infrastructure_topology_yaml(path)
    assert definition.external_nodes == ()
    assert definition.hardware == ()


def test_external_nodes_that_is_not_a_list_is_refused(tmp_path: Path):
    path = write(tmp_path / "topology.yml", "external_nodes: OVH\n")

    with pytest.raises(ValueError, match="external_nodes must be a list"):
        load_infrastructure_topology_yaml(path)


def test_hardware_that_is_not_a_list_is_refused(tmp_path: Path):
    path = write(tmp_path / "topology.yml", "hardware: GIGABYTE\n")

    with pytest.raises(ValueError, match="hardware must be a list"):
        load_infrastructure_topology_yaml(path)


def test_a_topology_that_is_not_a_mapping_is_refused(tmp_path: Path):
    path = write(tmp_path / "topology.yml", "- one\n- two\n")

    with pytest.raises(ValueError, match="mapping"):
        load_infrastructure_topology_yaml(path)


def test_order_is_preserved_from_the_source_file(tmp_path: Path):
    path = write(
        tmp_path / "topology.yml",
        """
        external_nodes:
          - name: OVH
            role: Registrar
          - name: Cloudflare
            role: DNS
        """,
    )

    definition = load_infrastructure_topology_yaml(path)
    assert [n.name for n in definition.external_nodes] == ["OVH", "Cloudflare"]


def test_dataclasses_default_to_empty_when_built_directly():
    assert InfrastructureTopologyDefinition().external_nodes == ()
    assert InfrastructureTopologyDefinition().hardware == ()
    assert ExternalNodeDefinition(name="Gmail", role="Messagerie").description == ""
    assert (
        HardwareProfileDefinition(
            name="Raspberry Pi",
            model="Raspberry Pi 3 Model B Rev 1.2",
            role="Reverse proxy",
            cpu="Broadcom BCM2837",
            ram="1 Go",
            storage="Carte micro SD",
            os_name="Debian (aarch64)",
        ).gpu
        is None
    )


# --------------------------------------------------------------------
# The real, shipped file
# --------------------------------------------------------------------


def test_the_real_infrastructure_topology_loads():
    """
    `src/aistack/architecture/definitions/infrastructure_topology.yml`
    is not a fixture — it is the real, hand-maintained topology
    `architecture_render.py` reads. A typo or a dropped field in the
    real file is caught here, the same discipline
    `test_the_real_service_categorization_loads` already applies.
    """

    repo_root = Path(__file__).resolve().parents[3]

    definition = load_infrastructure_topology_yaml(
        repo_root
        / "src"
        / "aistack"
        / "architecture"
        / "definitions"
        / "infrastructure_topology.yml"
    )

    node_names = [node.name for node in definition.external_nodes]
    assert node_names == ["OVH", "Cloudflare", "Freebox Ultra", "Gmail"]

    for node in definition.external_nodes:
        assert node.role
        assert node.description

    hardware_names = [profile.name for profile in definition.hardware]
    assert hardware_names == ["GIGABYTE", "Raspberry Pi"]

    by_name = {profile.name: profile for profile in definition.hardware}

    gigabyte = by_name["GIGABYTE"]
    assert gigabyte.model == "Gigabyte GA-MA770T-UD3"
    assert "Phenom" in gigabyte.cpu
    assert gigabyte.gpu == "NVIDIA Quadro P400 (GP107GL)"

    raspberry = by_name["Raspberry Pi"]
    assert raspberry.model == "Raspberry Pi 3 Model B Rev 1.2"
    assert "BCM2837" in raspberry.cpu
    assert raspberry.gpu is None

    for profile in definition.hardware:
        assert profile.role
        assert profile.ram
        assert profile.storage
        assert profile.os_name
