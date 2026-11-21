from __future__ import annotations

from aistack.config import configured

from pathlib import Path
from typing import Any

import yaml

from aistack.ai_runtime.policy import AIPolicy
from aistack.console.ai_use import ai_use_of
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
    policy: AIPolicy | None = None,
) -> tuple[ConsoleLink, ...]:
    """Load the declared console links from YAML.

    A card may declare `ai_callers`, the uses of a model its screen reaches (names of `ai_policy.yml`;
    `[]` for a screen that asks no engine). With `policy`, each card also gets `ai_use`: none, local
    engines only, or an outside engine too when the policy allows it (`ADR-0029` § 11).

    With `completing`, the file shipped with the package, the screens of AIStack it holds that `path`
    does not (same `service` and `path`) are added after the declared cards (`ADR-0017` § 1): a copy
    made before a screen existed still shows it, and a card the copy holds without `ai_callers` takes
    the shipped card's. Nothing is written; a card of the owner's is never
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
        links_data = _completed(links_data, completing)

    return tuple(
        _load_link(item, path, index, lang, declared, resolved_instance, policy)
        for index, item in enumerate(links_data)
    )


def _screen(item: Any) -> tuple[str, str] | None:
    """The `service` and `path` of a card that is a screen of AIStack; None for any other card."""

    if isinstance(item, dict) and "service" in item and "path" in item:
        return str(item["service"]), str(item["path"])

    return None


def _same_card(item: Any) -> tuple[str, str, str] | None:
    """What says two entries are the same card: the `service` and `path`, or the `url`."""

    if not isinstance(item, dict):
        return None

    if "service" in item:
        return ("service", str(item["service"]), str(item.get("path", "")))

    if "url" in item:
        return ("url", str(item["url"]), "")

    return None


def _completed(declared: list[Any], shipped_path: Path) -> list[Any]:
    """
    The declared cards, each given the `ai_callers` of the shipped card it is when it names none (a copy
    made before they existed), then the screens of AIStack the shipped file holds that they do not.
    """

    with shipped_path.open("r", encoding="utf-8") as stream:
        shipped = yaml.safe_load(stream)

    cards = shipped.get("links") if isinstance(shipped, dict) else None

    if not isinstance(cards, list):
        return declared

    callers = {
        key: card["ai_callers"]
        for card in cards
        if (key := _same_card(card)) is not None and "ai_callers" in card
    }
    held = {key for key in map(_screen, declared) if key is not None}

    given = [
        {**item, "ai_callers": callers[key]}
        if isinstance(item, dict) and "ai_callers" not in item and (key := _same_card(item)) in callers
        else item
        for item in declared
    ]

    return [*given, *(card for card in cards if _screen(card) is not None and _screen(card) not in held)]


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
    policy: AIPolicy | None = None,
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

    callers = _callers(data.get("ai_callers"), label)

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
        ai_callers=callers,
        ai_use=ai_use_of(callers, policy) if policy is not None else "",
    )


def _callers(raw: Any, label: str) -> tuple[str, ...] | None:
    if raw is None:
        return None

    if not isinstance(raw, list) or not all(isinstance(item, str) and item.strip() for item in raw):
        raise ValueError(f"{label}: ai_callers must be a list of names of uses of a model (or [])")

    return tuple(raw)
