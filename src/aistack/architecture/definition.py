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

    **`icon`/`href`/`description` are optional, added 2026-09-12**
    (`claude/PLAN-J11-CONSOLE-2026-09-11.md` §10). Until then only
    `name`/`container` traveled from `homepage/services.yaml` — see
    `ServiceCategorizationDefinition`'s own docstring for why that
    changed and what still does not travel (`server`). `icon` is a
    bare key into `renderers/architecture/vendor/icons/`
    (`load_icon_data_uri`), not a source-specific string like the
    original `nginx-proxy-manager.png`/`mdi-router-wireless`/
    `fa-user-tie` — the loader tries the vendored file conventions
    directly rather than a caller re-deriving one from the other.
    """

    name: str
    container: str | None = None
    icon: str | None = None
    href: str | None = None
    description: str | None = None


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
    provider can observe).

    **`name`/`container` traveled first, 2026-09-10; `icon`/`href`/
    `description` joined them 2026-09-12** (§10, richness gap against
    the pre-AIStack diagram, decided with the owner service field by
    service rather than assumed). `server` alone still does not
    travel, and does not on purpose: the source distinguishes
    Raspberry Pi from Gigabyte by which `docker-compose.yml`, on which
    host, declares a service — an observation AIStack has no provider
    for. The reconstructed diagram instead marks a service "observed"
    when its container is live in GIGABYTE's own Docker Catalog,
    "declared" otherwise (`claude/PLAN-J2-ARCHITECTURE-HTML-2026-09-10.md`,
    "Une réduction de périmètre assumée").
    """

    categories: tuple[ServiceCategoryDefinition, ...] = ()
