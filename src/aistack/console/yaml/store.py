from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from aistack.contracts.console_link import ConsoleLink
from aistack.contracts.instance_config import InstanceConfig
from aistack.i18n import Languages, default_languages, pick_localized

_REQUIRED_LINK_FIELDS = ("name", "description", "scope")


def load_console_links_yaml(
    path: Path,
    lang: str | None = None,
    languages: Languages | None = None,
    instance: InstanceConfig | None = None,
) -> tuple[ConsoleLink, ...]:
    """
    Load `PLAN-J11`'s declared console links from YAML.

    Mirrors `load_health_score_weights_yaml` field for field (written
    by hand, read-only, a missing key names which one and where) and
    in shape: one flat list, no per-host wrapper.

    **`name` and `description` may be localized, since 2026-09-27**
    (ADR-0010): either a plain string, the same in every language, or
    a mapping from language code to text, resolved here for `lang`
    (the reference language when `lang` is `None`). `url` is never
    localized — where a service lives does not depend on who reads
    the card.

    **`scope`, added 2026-09-30, is never localized either** — same
    reason as `url`: whether a card is LAN-only or public does not
    depend on who reads the card, so it is read as a plain string, not
    passed through `pick_localized`.

    **`url` vs `service`, 2026-09-30 (R10)** — an entry declares
    exactly one. `url` still carries a literal exactly as the owner
    typed it (a relative path such as `/health.html`, for the two
    cards this console serves itself). `service` names a key in
    `instance` (`aistack.contracts.instance_config.InstanceConfig`,
    defaulting to the real `instance_config.yml` when `instance` is
    not given, the same "a caller may supply its own, tests do"
    convention `languages` already follows above) — resolved to
    `InstanceConfig.service_url(service)`, the same
    `http://<host>:<port>` shape these five cards used to hand-type.
    Declaring both, or neither, is refused: one card, one real
    address, never two disagreeing sources for it.
    """

    declared = languages if languages is not None else default_languages()
    resolved_instance = instance if instance is not None else _default_instance()

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
        _load_link(item, path, index, lang, declared, resolved_instance)
        for index, item in enumerate(links_data)
    )


def _default_instance() -> InstanceConfig:
    # Deferred import: `aistack.instance.yaml` is a separate small
    # package (definitions/instance_config.yml, its own loader),
    # imported here rather than at module level so a caller that
    # always supplies its own `instance` (every test above) never
    # pays for reading a second file it does not need.
    from aistack.instance.yaml import load_instance_config_yaml

    default_path = (
        Path(__file__).resolve().parents[2]
        / "instance"
        / "definitions"
        / "instance_config.yml"
    )
    return load_instance_config_yaml(default_path)


def _load_link(
    data: Any,
    path: Path,
    index: int,
    lang: str | None,
    languages: Languages,
    instance: InstanceConfig,
) -> ConsoleLink:
    label = f"console link definition {path}: links[{index}]"

    if not isinstance(data, dict):
        raise ValueError(f"{label} must be a mapping")

    missing = [field for field in _REQUIRED_LINK_FIELDS if field not in data]

    if missing:
        raise ValueError(f"{label} is missing: {', '.join(missing)}")

    has_url = "url" in data
    has_service = "service" in data

    if has_url and has_service:
        raise ValueError(f"{label} declares both url and service — expected one")

    if not has_url and not has_service:
        raise ValueError(f"{label} is missing: url or service")

    if has_service:
        try:
            url = instance.service_url(str(data["service"]))
        except ValueError as error:
            raise ValueError(f"{label}: {error}") from error
    else:
        url = data["url"]

    return ConsoleLink(
        name=pick_localized(data["name"], lang, languages, f"{label}.name"),
        description=pick_localized(
            data["description"], lang, languages, f"{label}.description"
        ),
        url=url,
        scope=data["scope"],
    )
