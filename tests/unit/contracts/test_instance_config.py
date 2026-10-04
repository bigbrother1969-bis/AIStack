import pytest

from aistack.contracts.instance_config import InstanceConfig


def test_a_complete_instance_config_is_accepted():
    config = InstanceConfig(
        lan_hostname="GIGABYTE",
        service_ports={"console": 8183, "selection_ui": 8181},
    )

    assert config.lan_hostname == "GIGABYTE"
    assert config.service_ports == {"console": 8183, "selection_ui": 8181}


def test_an_empty_hostname_is_refused():
    with pytest.raises(ValueError, match="no LAN hostname"):
        InstanceConfig(lan_hostname="", service_ports={"console": 8183})


def test_a_blank_hostname_is_refused():
    with pytest.raises(ValueError, match="no LAN hostname"):
        InstanceConfig(lan_hostname="   ", service_ports={"console": 8183})


def test_no_service_ports_is_refused():
    with pytest.raises(ValueError, match="no service ports"):
        InstanceConfig(lan_hostname="GIGABYTE", service_ports={})


def test_a_nameless_service_is_refused():
    with pytest.raises(ValueError, match="nameless service"):
        InstanceConfig(lan_hostname="GIGABYTE", service_ports={"": 8183})


def test_a_port_out_of_range_is_refused():
    with pytest.raises(ValueError, match="port out of range"):
        InstanceConfig(lan_hostname="GIGABYTE", service_ports={"console": 70000})


def test_a_zero_port_is_refused():
    with pytest.raises(ValueError, match="port out of range"):
        InstanceConfig(lan_hostname="GIGABYTE", service_ports={"console": 0})


def test_service_url_assembles_host_and_port():
    config = InstanceConfig(
        lan_hostname="GIGABYTE", service_ports={"console": 8183}
    )

    assert config.service_url("console") == "http://GIGABYTE:8183"


def test_service_url_for_an_undeclared_service_is_refused():
    config = InstanceConfig(
        lan_hostname="GIGABYTE", service_ports={"console": 8183}
    )

    with pytest.raises(ValueError, match="no port for 'timemachine_ui'"):
        config.service_url("timemachine_ui")


def test_the_phase_is_production_unless_said_and_nothing_else_is_accepted():
    import pytest as _pytest

    from aistack.contracts.instance_config import InstanceConfig as Config

    assert Config(lan_hostname="G", service_ports={"console": 8183}).in_development is False
    assert Config(lan_hostname="G", service_ports={"console": 8183}, phase="development").in_development
    with _pytest.raises(ValueError):
        Config(lan_hostname="G", service_ports={"console": 8183}, phase="staging")
