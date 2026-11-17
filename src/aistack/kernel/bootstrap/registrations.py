from __future__ import annotations

import importlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from aistack.kernel import Kernel

# The declared registrations of the package the Kernel is installed in.
DEFAULT_REGISTRATIONS = Path(__file__).resolve().parents[2] / "registrations.yml"

PROVIDERS = "providers"
CATALOG_VIEWS = "catalog_views"
TASKS = "tasks"

# In the order they are registered: a task is built on a provider.
KINDS = (PROVIDERS, CATALOG_VIEWS, TASKS)


@dataclass(frozen=True)
class Registration:
    """
    One declared registration: what to build, and the identifier it is
    registered under. `provider` names the registered provider a task
    is built on; it is empty for everything else. `all_providers`
    marks a task built on the whole provider registry, for a chain
    that reads several providers (a task declares one or the other).
    """

    kind: str
    identifier: str
    factory: str
    provider: str = ""
    all_providers: bool = False


def load_registrations(path: Path = DEFAULT_REGISTRATIONS) -> tuple[Registration, ...]:
    """
    Read the declared registrations (ADR-0027 § 8), in the order of
    `KINDS` and, within a kind, in the order of the file.

    The file is hand-written: a missing key, an unknown kind or a
    malformed entry raises a ValueError naming it and where.
    """

    with path.open("r", encoding="utf-8") as stream:
        try:
            data = yaml.safe_load(stream)
        except yaml.YAMLError as error:
            raise ValueError(f"Kernel registrations {path} are not valid YAML: {error}") from error

    if not isinstance(data, dict):
        raise ValueError(f"Kernel registrations must contain a mapping: {path}")

    unknown = sorted(set(data) - set(KINDS))
    if unknown:
        raise ValueError(f"Kernel registrations {path} declare unknown kinds: {unknown}; known: {list(KINDS)}")

    registrations: list[Registration] = []

    for kind in KINDS:
        entries = data.get(kind) or []
        if not isinstance(entries, list):
            raise ValueError(f"Kernel registrations {path}: {kind} must be a list")

        for index, entry in enumerate(entries):
            where = f"{path}: {kind}[{index}]"
            if not isinstance(entry, dict):
                raise ValueError(f"Kernel registration {where} must be a mapping")

            allowed = {"id", "factory", "provider", "all_providers"} if kind == TASKS else {"id", "factory"}
            extra = sorted(set(entry) - allowed)
            if extra:
                raise ValueError(f"Kernel registration {where} declares unknown keys: {extra}")

            for key in ("id", "factory"):
                if not isinstance(entry.get(key), str) or not entry[key].strip():
                    raise ValueError(f"Kernel registration {where} is missing: {key}")

            provider = entry.get("provider", "")
            if not isinstance(provider, str):
                raise ValueError(f"Kernel registration {where}: provider must be an identifier")

            all_providers = entry.get("all_providers", False)
            if not isinstance(all_providers, bool):
                raise ValueError(f"Kernel registration {where}: all_providers must be true or false")
            if all_providers and provider.strip():
                raise ValueError(
                    f"Kernel registration {where}: a task is built on one provider or on all of them, not both"
                )

            registrations.append(
                Registration(
                    kind=kind,
                    identifier=entry["id"].strip(),
                    factory=entry["factory"].strip(),
                    provider=provider.strip(),
                    all_providers=all_providers,
                )
            )

    return tuple(registrations)


def resolve_factory(registration: Registration) -> Any:
    """The class a registration names as `module:Class`."""

    module_name, separator, attribute = registration.factory.partition(":")
    if not separator or not module_name or not attribute:
        raise ValueError(
            f"Kernel registration {registration.kind} {registration.identifier!r}: "
            f"factory {registration.factory!r} is not written module:Class"
        )

    try:
        module = importlib.import_module(module_name)
    except ImportError as error:
        raise ValueError(
            f"Kernel registration {registration.kind} {registration.identifier!r}: "
            f"cannot import {module_name!r}: {error}"
        ) from error

    try:
        return getattr(module, attribute)
    except AttributeError:
        raise ValueError(
            f"Kernel registration {registration.kind} {registration.identifier!r}: "
            f"{module_name!r} has no {attribute!r}"
        ) from None


def register_declared(kernel: Kernel, registrations: tuple[Registration, ...]) -> None:
    """
    Build and register every declared registration into the Kernel.

    A task that names a provider is built on the instance already
    registered under that identifier, never on a second one.
    """

    for registration in registrations:
        factory = resolve_factory(registration)

        if registration.kind == PROVIDERS:
            kernel.registries.providers.register(registration.identifier, factory())
        elif registration.kind == CATALOG_VIEWS:
            kernel.registries.catalog_views.register(registration.identifier, factory())
        elif registration.all_providers:
            kernel.registries.tasks.register(registration.identifier, factory(kernel.registries.providers))
        elif registration.provider:
            if registration.provider not in kernel.registries.providers:
                raise ValueError(
                    f"Kernel registration tasks {registration.identifier!r} is built on "
                    f"provider {registration.provider!r}, which is not registered"
                )
            try:
                provider = kernel.registries.providers.collecting(registration.provider)
            except TypeError as error:
                raise ValueError(
                    f"Kernel registration tasks {registration.identifier!r}: {error}"
                ) from error
            kernel.registries.tasks.register(registration.identifier, factory(provider))
        else:
            kernel.registries.tasks.register(registration.identifier, factory())
