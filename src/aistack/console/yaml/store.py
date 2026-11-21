from __future__ import annotations

from aistack.config import configured

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
    completing: Path | None = None,
) -> tuple[ConsoleLink, ...]:
    """Load the declared console links from YAML.

    With `completing`, the file shipped with the package, the screens of AIStack it holds that `path`
    does not (same `service` and `path`) are added after the declared cards (`ADR-0017` § 1): a copy
    made before a screen existed still shows it. Nothing is written; a card of the owner's is never
    changed; a screen he removed from a copy comes back.

    `name`, `description` and `ai` may be localized (ADR-0010): a plain
    string or a mapping from language code to text, resolved for `lang`.
    `url` and `scope` are never localized.

    Each entry declares exactly one of `url` (a literal, e.g. `/health.html`)
    or `service`, a key of `instance` resolved through
    `InstanceConfig.service_url`, optionally followed by `path`. `instance`
    defaults to the shipped `instance_config.yml`.
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

    if completing is not None and completing.resolve() != path.resolve():
        links_data = [*links_data, *_missing_screens(links_data, completing)]

    return tuple(
        _load_link(item, path, index, lang, declared, resolved_instance)
        for index, item in enumerate(links_data)
    )


def _screen(item: Any) -> tuple[str, str] | None:
    """The `service` and `path` of a card that is a screen of AIStack; None for any other card."""

    if isinstance(item, dict) and "service" in item and "path" in item:
        return str(item["service"]), str(item["path"])

    return None


def _missing_screens(declared: list[Any], shipped_path: Path) -> list[Any]:
    """The cards of the shipped file that are screens of AIStack the declared cards do not hold."""

    with shipped_path.open("r", encoding="utf-8") as stream:
        shipped = yaml.safe_load(stream)

    cards = shipped.get("links") if isinstance(shipped, dict) else None

    if not isinstance(cards, list):
        return []

    held = {key for key in map(_screen, declared) if key is not None}

    return [card for card in cards if _screen(card) is not None and _screen(card) not in held]


def _default_instance() -> InstanceConfig:
    # Deferred so callers that pass their own `instance` never read this file.
    from aistack.instance.yaml import load_instance_config_yaml

    default_path = (
        configured(Path(__file__).resolve().parents[2]
        / "instance"
        / "definitions"
        / "instance_config.yml")
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

    if "path" in data and not has_service:
        raise ValueError(f"{label} declares a path without a service")

    if has_service:
        try:
            url = instance.service_url(str(data["service"]))
        except ValueError as error:
            raise ValueError(f"{label}: {error}") from error

        # ADR-0012: a screen of the single web application lives under a path on
        # the LAN listener (`service: web_lan`, `path: /network-discovery/`).
        if "path" in data:
            path_part = str(data["path"])

            if not path_part.startswith("/"):
                raise ValueError(f"{label}: path must start with /, got {path_part!r}")

            url += path_part
    else:
        url = data["url"]

    return ConsoleLink(
        name=pick_localized(data["name"], lang, languages, f"{label}.name"),
        description=pick_localized(
            data["description"], lang, languages, f"{label}.description"
        ),
        url=url,
        scope=data["scope"],
        # Optional: what the screen asks of the AI.
        ai=(
            pick_localized(data["ai"], lang, languages, f"{label}.ai")
            if data.get("ai")
            else ""
        ),
    )
