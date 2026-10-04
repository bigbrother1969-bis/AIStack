"""
Who publishes the console (2026-10-03): the values its left column, its
legal notice and its licence page show, declared by the owner in
`definitions/console_identity.yml` — never discovered, never guessed.
A missing field is an error, not a blank on a public legal page.
"""

from __future__ import annotations

from aistack.config import configured

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from aistack.i18n import Languages, default_languages, pick_localized

DEFAULT_IDENTITY = configured(Path(__file__).resolve().parent / "definitions" / "console_identity.yml")

_REQUIRED = (
    "publisher",
    "legal_form",
    "siren",
    "city",
    "publication_director",
    "contact_url",
    "copyright_year",
    "license",
    "license_url",
    "repositories",
)


@dataclass(frozen=True)
class Repository:
    name: str
    url: str


@dataclass(frozen=True)
class ContainerImage:
    """A published container image: its name, the registry that serves
    it and that registry's page for it."""

    name: str
    registry: str
    url: str


@dataclass(frozen=True)
class ConsoleIdentity:
    publisher: str
    legal_form: str
    siren: str
    city: str
    publication_director: str
    contact_url: str
    copyright_year: int
    license: str
    license_url: str
    repositories: tuple[Repository, ...]
    images: tuple[ContainerImage, ...] = ()


def load_console_identity(
    path: Path = DEFAULT_IDENTITY,
    lang: str | None = None,
    languages: Languages | None = None,
) -> ConsoleIdentity:
    declared = languages if languages is not None else default_languages()

    with path.open("r", encoding="utf-8") as stream:
        data: Any = yaml.safe_load(stream)

    if not isinstance(data, dict):
        raise ValueError(f"console identity {path} must be a mapping")

    missing = [field for field in _REQUIRED if not data.get(field)]

    if missing:
        raise ValueError(f"console identity {path} is missing: {', '.join(missing)}")

    for url_field in ("contact_url", "license_url"):
        if not str(data[url_field]).startswith("https://"):
            raise ValueError(f"console identity {path}: {url_field} must be an https:// address")

    repositories = tuple(
        Repository(name=str(entry["name"]), url=str(entry["url"])) for entry in data["repositories"]
    )

    images = tuple(
        ContainerImage(
            name=str(entry["name"]), registry=str(entry["registry"]), url=str(entry["url"])
        )
        for entry in data.get("images") or ()
    )

    for image in images:
        if not image.url.startswith("https://"):
            raise ValueError(f"console identity {path}: image {image.name} must have an https:// address")

    return ConsoleIdentity(
        publisher=str(data["publisher"]),
        legal_form=pick_localized(data["legal_form"], lang, declared, f"{path}: legal_form"),
        siren=str(data["siren"]),
        city=str(data["city"]),
        publication_director=str(data["publication_director"]),
        contact_url=str(data["contact_url"]),
        copyright_year=int(data["copyright_year"]),
        license=str(data["license"]),
        license_url=str(data["license_url"]),
        repositories=repositories,
        images=images,
    )
