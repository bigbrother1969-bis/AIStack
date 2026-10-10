from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ServiceDefinition:
    """
    One service as the user categorizes it, not as Docker reports it.

    `container` is optional: some services run on hardware with no provider
    or are reached without a container of their own. `icon` is a bare key
    into `renderers/architecture/vendor/icons/` (see `load_icon_data_uri`).
    An `on_demand` service is started only when needed, so its container
    being absent is never reported as an inventory gap.
    """

    name: str
    container: str | None = None
    icon: str | None = None
    href: str | None = None
    description: str | None = None
    on_demand: bool = False


@dataclass(frozen=True)
class ServiceCategoryDefinition:
    """
    One category and its services, in the order the source file lists them.
    """

    name: str
    services: tuple[ServiceDefinition, ...] = ()


@dataclass(frozen=True)
class ServiceCategorizationDefinition:
    """
    Which category each service belongs to, loaded from
    `service_categorization.yml`.

    This is a user decision no provider can observe. Which host runs a
    service is not declared here; the graph marks a service "observed" when
    its container is live, "declared" otherwise.
    """

    categories: tuple[ServiceCategoryDefinition, ...] = ()
