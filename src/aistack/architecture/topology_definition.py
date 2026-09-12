from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExternalNodeDefinition:
    """
    One piece of infrastructure outside AIStack's own observation reach
    — a registrar, a DNS/CDN provider, the internet box, an email
    provider. No `DockerProvider`/`ComposeProvider`-style collector
    exists for any of these (`PLAN-J11-CONSOLE-2026-09-11.md` §10:
    "aucune donnée AIStack ne couvre ça aujourd'hui") — this is a pure
    declaration, the owner's own account of what each node is for,
    the same governance stance `ServiceCategorizationDefinition`
    already takes for which category a service belongs to.

    `role` is the short label (e.g. "Registrar de noms de domaine");
    `description` is the fuller account. Both are the owner's own
    words, confirmed one node at a time, 2026-09-12 — never inferred
    from what a node's product category usually does.
    """

    name: str
    role: str
    description: str = ""


@dataclass(frozen=True)
class HardwareProfileDefinition:
    """
    One physical host's own fiche — what it *is*, not how it is
    currently performing. `cpu`/`ram`/`gpu`/`storage`/`os` are static
    inventory facts, gathered by hand from `lscpu`/`free -h`/
    `dmidecode`/`lsblk` run on each host (GIGABYTE) or from the
    device's own `/proc/device-tree/model` plus its official spec
    sheet (Raspberry Pi 3 Model B's CPU/RAM, `raspberrypi.com`) —
    never derived from a running-usage metric.

    **Deliberately distinct from the Health Cockpit's own GPU/storage
    metrics** (`PLAN-J11-CONSOLE-2026-09-11.md` §10, "Stockage/
    Sauvegarde-PRA/GPU" — link, don't duplicate): that decision was
    about *usage* (how full, how hot, how loaded); `gpu`/`storage`
    here are inventory (which GPU exists, how much storage exists at
    all) — the owner confirmed keeping both is not a duplication,
    2026-09-12.

    `gpu` is optional — the Raspberry Pi has none.
    """

    name: str
    model: str
    role: str
    cpu: str
    ram: str
    storage: str
    os_name: str
    gpu: str | None = None


@dataclass(frozen=True)
class InfrastructureTopologyDefinition:
    """
    The whole governed shape of "what exists outside the services
    graph" — external nodes and hardware fiches, together, because
    both answer the same gap identified against the pre-AIStack
    `architecture.html` (§10's first bullet: "Topologie réseau externe
    ... et fiches matérielles").

    Either sequence may be empty — a topology with hardware but no
    external nodes declared yet (or vice versa) is not an error, it is
    simply incomplete; `render_html` renders only the sub-sections
    that have content.
    """

    external_nodes: tuple[ExternalNodeDefinition, ...] = ()
    hardware: tuple[HardwareProfileDefinition, ...] = ()
