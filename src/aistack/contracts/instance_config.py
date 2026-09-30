from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class InstanceConfig:
    """
    AIStack's own address on this deployment — closes `ROADMAP-1.2-TO-
    2.0-2026-09-27.md`'s R10: "`GIGABYTE:8181`, `/srv/aistack`,
    `persiaut-family.fr` sont écrits en dur : incompatible avec un
    AIStack qui s'adapte au réseau découvert." Scoped, at the owner's
    own cadrage (2026-09-30), to AIStack's own address alone — the
    console and its five mini-apps, the one place a stale value
    actually breaks the console's own links if the LAN host or a
    port ever changes. `/srv/aistack` (a systemd `WorkingDirectory`/
    `ExecStart` path, needed before any Python process starts — the
    same chicken-and-egg every `deploy/systemd/*.service` unit and
    `run_*.sh` launcher already has) and the third-party service
    directory (`service_categorization.yml`, `cmdb_probe_targets.yml`
    — links to Jellyfin, Nextcloud and the rest, a different kind of
    fact the owner declares by hand, not AIStack's own identity)
    stay outside this contract, deliberately (`ARC-P-006`).

    **Declared, not discovered** — the same "never guessed" discipline
    `ConsoleLink` and `ServiceCategorizationDefinition` already hold:
    nothing in this heritage probes for AIStack's own LAN address or
    which port a mini-app answers on. `console_links.yml`'s own header
    comment already narrates, by hand, that each port was the "next
    free port" the owner picked when a mini-app was added — a real
    decision, not a fact any provider could observe. What changes here
    is not who decides it, but how many places have to be told: one
    file instead of six hand-typed `http://GIGABYTE:818X` literals
    (`console_links.yml`'s five `url:` fields plus `timemachine_ui
    .app`'s own `_CONSOLE_BASE_URL`) and seven more hardcoded directly
    in the other four mini-apps' own templates (`network_discovery_ui`,
    `priority_ui`, `selection_ui`, `troubleshooting_assistant_ui` —
    found not going through `aistack.renderers.nav.render_page_nav`'s
    own `console_base_url` parameter at all, each hand-rolling its own
    "back to console" link instead).

    `lan_hostname` names the single LAN host every AIStack service
    answers on today (`GIGABYTE`) — this heritage runs every mini-app
    on the one host it observes itself from, never a mix of hosts, so
    one hostname for every `service_ports` entry is a real fact, not a
    simplification papering over a case that does not exist yet
    (`ARC-P-006`).
    """

    lan_hostname: str
    service_ports: Mapping[str, int]

    def __post_init__(self) -> None:
        if not self.lan_hostname.strip():
            raise ValueError("an instance config names no LAN hostname")

        if not self.service_ports:
            raise ValueError("an instance config declares no service ports")

        for service, port in self.service_ports.items():
            if not service.strip():
                raise ValueError("an instance config names a nameless service")

            if not (0 < port < 65536):
                raise ValueError(
                    f"{service} declares a port out of range: {port}"
                )

    def service_url(self, service: str) -> str:
        """
        `http://<lan_hostname>:<port>` for `service` — the one place
        this shape is assembled, the same "resolve it once, not at
        every call site" discipline `aistack.timemachine.iri`'s own
        IRI builders already hold. Raises when `service` names
        nothing this instance declares a port for, the same "a
        missing fact is an error, never a silent default" discipline
        `ConsoleLink`'s own validation already holds — never a guess
        at what port a service unknown here might answer on.
        """

        if service not in self.service_ports:
            known = ", ".join(sorted(self.service_ports)) or "(none)"
            raise ValueError(
                f"instance config declares no port for {service!r} — "
                f"known: {known}"
            )

        return f"http://{self.lan_hostname}:{self.service_ports[service]}"
