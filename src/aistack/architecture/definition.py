from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ServiceDefinition:
    """
    One service, as the owner categorizes it — not as Docker reports it.

    **`container` is optional, and absence is meaningful.** Pi-hole,
    FreeboxOS, LibreSpeed, Architecture Homelab, Indy and Music Sync
    (`homepage/services.yaml`, ported 2026-09-10) name no container at
    all — some run on hardware AIStack has no provider for (the
    Freebox itself), some are reached through it without being a
    container of their own. The graph-building step
    (`PLAN-J2-ARCHITECTURE-HTML-2026-09-10.md`, step 3) is what turns
    this absence, or a name present here but absent from GIGABYTE's
    own Docker Catalog, into "declared but not observed" — this
    dataclass only carries the declaration.
    """

    name: str
    container: str | None = None


@dataclass(frozen=True)
class ServiceCategoryDefinition:
    """
    One category and the services the owner placed in it.

    Order is preserved from the source file — `homepage/services.yaml`
    lists categories and services in the order they appear on the
    owner's own dashboard, and nothing about that order is derived
    from Docker or Compose, so there is nothing to sort it against.
    """

    name: str
    services: tuple[ServiceDefinition, ...] = ()


@dataclass(frozen=True)
class ServiceCategorizationDefinition:
    """
    The whole governed shape of "which category is this service in".

    **Ported, not designed** — `homepage/services.yaml` (found on the
    laptop's `/mnt/backup/homelab_documentation`, the pre-AIStack
    architecture.html generator) already answers this question; this
    is that answer, read into a typed shape (GOV-P-001: a
    categorization is the owner's own decision, not something a
    provider can observe). Only `name`/`container` travel from the
    source file — `icon`, `href`, `description` and `server` are
    Homepage-dashboard concerns the reconstructed diagram (J2) does
    not use. `server` in particular does not travel on purpose: the
    source distinguishes Raspberry Pi from Gigabyte by which
    `docker-compose.yml`, on which host, declares a service — an
    observation AIStack has no provider for. The reconstructed diagram
    instead marks a service "observed" when its container is live in
    GIGABYTE's own Docker Catalog, "declared" otherwise
    (`claude/PLAN-J2-ARCHITECTURE-HTML-2026-09-10.md`, "Une réduction
    de périmètre assumée").
    """

    categories: tuple[ServiceCategoryDefinition, ...] = ()
