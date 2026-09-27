from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from aistack.contracts.console_link import ConsoleLink
from aistack.i18n import Languages, default_languages, pick_localized

_REQUIRED_LINK_FIELDS = ("name", "description", "url")


def load_console_links_yaml(
    path: Path, lang: str | None = None, languages: Languages | None = None
) -> tuple[ConsoleLink, ...]:
    """
    Load `PLAN-J11`'s declared console links from YAML.

    Mirrors `load_health_score_weights_yaml` field for field (written
    by hand, read-only, a missing key names which one and where) and
    in shape: one flat list, no per-host wrapper — a `ConsoleLink`'s
    `url` already carries whatever host-specific fact it names
    (`GIGABYTE:8181`, a relative `/health.html`), so there is nothing
    left for this loader itself to scope by host.

    **`name` and `description` may be localized, since 2026-09-27**
    (ADR-0010): either a plain string, the same in every language, or
    a mapping from language code to text, resolved here for `lang`
    (the reference language when `lang` is `None`). `url` is never
    localized — where a service lives does not depend on who reads
    the card.
    """

    declared = languages if languages is not None else default_languages()

    with path.open("r", encoding="utf-8") as stream:
        try:
            data = yaml.safe_load(stream)
        except yaml.YAMLError as error:
            raise ValueError(
                f"console link definition {path} is not valid YAML: {error}"
            ) from error

    if not isinstance(data, dict):
        raise ValueError(f"console link definition must contain a mapping: {path}")

    if "links" not in data:
        raise ValueError(f"console link definition {path} is missing: links")

    links_data = data["links"]

    if not isinstance(links_data, list):
        raise ValueError(f"console link definition {path}: links must be a list")

    return tuple(
        _load_link(item, path, index, lang, declared)
        for index, item in enumerate(links_data)
    )


def _load_link(
    data: Any, path: Path, index: int, lang: str | None, languages: Languages
) -> ConsoleLink:
    label = f"console link definition {path}: links[{index}]"

    if not isinstance(data, dict):
        raise ValueError(f"{label} must be a mapping")

    missing = [field for field in _REQUIRED_LINK_FIELDS if field not in data]

    if missing:
        raise ValueError(f"{label} is missing: {', '.join(missing)}")

    return ConsoleLink(
        name=pick_localized(data["name"], lang, languages, f"{label}.name"),
        description=pick_localized(
            data["description"], lang, languages, f"{label}.description"
        ),
        url=data["url"],
    )
