"""
`aistack.catalog.linux_services.LinuxServicesCatalogBuilder` (`ADR-0035`,
LS2) — the same shape as `DockerRuntimeCatalogBuilder`
(`tests/unit/catalog/docker/test_runtime_catalog.py`), but its own
catalog: grounded by reading the repository (2026-11-28), no existing
Runtime Catalog covers a network-scanned host to extend into, and
`network_docker.discover` — LS1's own precedent — has no Runtime
Catalog step either.
"""

from __future__ import annotations

from aistack.catalog.linux_services import LinuxServicesCatalogBuilder
from aistack.kernel.catalog import Catalog


def observation(*hosts: dict) -> dict:
    return {
        "provider": {"id": "aistack.provider.linux_services"},
        "collected_at": "2026-11-28T12:00:00+00:00",
        "linux_services": {"cidr": "192.168.1.0/24", "hosts": list(hosts)},
    }


def host(host: str, *services: dict, ssh_username: str = "pi") -> dict:
    return {"host": host, "ssh_username": ssh_username, "services": list(services)}


def service(
    name: str,
    *,
    unit_state: str = "active",
    listening_ports: list[int] | None = None,
    package_version: str | None = "1.0",
    config_path: str | None = "/etc/example.conf",
    observed_at: str = "2026-11-28T12:00:00+00:00",
) -> dict:
    entry = {
        "service": name,
        "unit_state": unit_state,
        "listening_ports": listening_ports or [],
        "config_path": config_path,
        "observed_at": observed_at,
    }
    if package_version is not None:
        entry["package_version"] = package_version
    return entry


def test_the_builder_returns_a_governed_catalog():
    catalog = LinuxServicesCatalogBuilder().build(
        observation(host("192.168.1.40", service("mariadb")))
    )

    assert isinstance(catalog, Catalog)
    assert catalog.catalog_id == "linux-services-runtime"
    assert catalog.metadata["source_provider"] == "aistack.provider.linux_services"
    assert catalog.metadata["collected_at"] == "2026-11-28T12:00:00+00:00"
    assert catalog.metadata["cidr"] == "192.168.1.0/24"


def test_one_item_per_host_service_pair():
    catalog = LinuxServicesCatalogBuilder().build(
        observation(
            host("192.168.1.40", service("mariadb"), service("apache")),
            host("192.168.1.41", service("postgresql")),
        )
    )

    assert [item.id for item in catalog.items] == [
        "192.168.1.40/mariadb",
        "192.168.1.40/apache",
        "192.168.1.41/postgresql",
    ]
    assert all(item.kind == "linux_service" for item in catalog.items)


def test_every_field_of_the_declared_schema_reaches_the_metadata():
    catalog = LinuxServicesCatalogBuilder().build(
        observation(
            host(
                "192.168.1.40",
                service(
                    "mariadb",
                    unit_state="active",
                    listening_ports=[3306],
                    package_version="1:10.11.6",
                    config_path="/etc/mysql/mariadb.conf.d/50-server.cnf",
                    observed_at="2026-11-28T12:00:00+00:00",
                ),
                ssh_username="pi",
            )
        )
    )

    metadata = catalog.items[0].metadata
    assert metadata == {
        "host": "192.168.1.40",
        "ssh_username": "pi",
        "service": "mariadb",
        "unit_state": "active",
        "listening_ports": "3306",
        "package_version": "1:10.11.6",
        "config_path": "/etc/mysql/mariadb.conf.d/50-server.cnf",
        "observed_at": "2026-11-28T12:00:00+00:00",
    }


def test_a_partial_observation_is_kept_not_dropped():
    """LS1's own decision (AskUserQuestion, 2026-11-28): a host with no
    dpkg/rpm is a partial observation, never an exclusion."""

    catalog = LinuxServicesCatalogBuilder().build(
        observation(
            host(
                "192.168.1.40",
                service("mariadb", package_version=None, config_path=None),
            )
        )
    )

    metadata = catalog.items[0].metadata
    assert metadata["package_version"] == ""
    assert metadata["config_path"] == ""


def test_listening_ports_are_sorted_and_comma_joined():
    catalog = LinuxServicesCatalogBuilder().build(
        observation(host("192.168.1.40", service("apache", listening_ports=[443, 80])))
    )

    assert catalog.items[0].metadata["listening_ports"] == "80,443"


def test_no_listening_ports_reads_as_empty_not_none():
    catalog = LinuxServicesCatalogBuilder().build(
        observation(host("192.168.1.40", service("apache", listening_ports=[])))
    )

    assert catalog.items[0].metadata["listening_ports"] == ""


def test_every_metadata_value_is_a_string():
    catalog = LinuxServicesCatalogBuilder().build(
        observation(host("192.168.1.40", service("mariadb", package_version=None, config_path=None)))
    )

    assert all(type(value) is str for value in catalog.items[0].metadata.values())


def test_no_host_reached_is_an_empty_catalog_not_an_error():
    catalog = LinuxServicesCatalogBuilder().build(observation())

    assert catalog.items == ()
