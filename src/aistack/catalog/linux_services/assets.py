from __future__ import annotations

from typing import Any

from aistack.kernel.catalog import Catalog, CatalogItem


class LinuxServicesCatalogBuilder:
    """Build a Catalog from a raw Linux services discovery observation
    (`ADR-0035`).

    The same shape as `DockerRuntimeCatalogBuilder`, but its own
    catalog: unlike Docker's local provider, no existing Runtime
    Catalog covers a network-scanned host to extend into (grounded by
    reading the repository, 2026-11-28 — `network_docker.discover`,
    LS1's own precedent, has no Runtime Catalog step either, it only
    writes its raw observation).

    One flat catalog, one item per (host, service) pair observed among
    the four targets — MariaDB/MySQL, PostgreSQL, Apache, PHP.
    Identifiers are unique within this catalog only, the same
    convention as Docker's.
    """

    KIND = "linux_service"

    def build(self, observation: dict[str, Any]) -> Catalog:
        linux_services = observation["linux_services"]

        return Catalog(
            catalog_id="linux-services-runtime",
            title="Linux Services Runtime Catalog",
            metadata={
                "source_provider": observation["provider"]["id"],
                "collected_at": observation["collected_at"],
                "cidr": self._text(linux_services.get("cidr")),
            },
            items=tuple(
                self._item(host_entry, service)
                for host_entry in linux_services["hosts"]
                for service in host_entry["services"]
            ),
        )

    def _item(self, host_entry: dict[str, Any], service: dict[str, Any]) -> CatalogItem:
        host = self._text(host_entry.get("host"))
        name = self._text(service.get("service"))

        return CatalogItem(
            id=f"{host}/{name}",
            label=f"{name} ({host})",
            kind=self.KIND,
            source=host,
            metadata={
                "host": host,
                "ssh_username": self._text(host_entry.get("ssh_username")),
                "service": name,
                "unit_state": self._text(service.get("unit_state")),
                "listening_ports": self._sorted_csv(service.get("listening_ports")),
                "package_version": self._text(service.get("package_version")),
                "config_path": self._text(service.get("config_path")),
                "observed_at": self._text(service.get("observed_at")),
            },
        )

    def _text(self, value: Any) -> str:
        """`str(value)`, with `None` as `""` (metadata values are strings)."""

        return "" if value is None else str(value)

    def _sorted_csv(self, value: Any) -> str:
        """A list of ports as a sorted, comma-joined field, the same
        convention as Docker's own catalog builder."""

        if not value:
            return ""

        return ",".join(str(port) for port in sorted(value))
