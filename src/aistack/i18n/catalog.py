from __future__ import annotations

from aistack.config import configured

import base64
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

# ADR-0010 (User Interface Localization). The two files every
# localized screen reads, resolved `Path(__file__)`-relative — the
# same convention every other `definitions/` directory in this package
# already holds (`console_links.yml`, `pra_tests.yml`), so a real,
# non-editable install carries them through
# `[tool.setuptools.package-data]`'s `**/*.yml` without anything new
# being declared.
DEFAULT_LANGUAGES = configured(Path(__file__).resolve().parent / "definitions" / "languages.yml")
DEFAULT_CATALOGS = Path(__file__).resolve().parent / "catalogs"


@dataclass(frozen=True)
class Language:
    """
    One interface language, as `languages.yml` declares it.

    `flag` is the declared flag as a `data:` URI, ready for an `<img>`
    in any page — the console's pages are single files and the
    mini-apps serve no static files, so an image travels inside the
    markup, the same way the console's lockup already does. Empty when
    the language declares no flag: its switch then shows `name`.
    """

    code: str
    name: str
    flag: str = ""


@dataclass(frozen=True)
class Languages:
    """
    The declared interface languages and which one is the reference.

    `reference` is always one of `available` — `load_languages_yaml`
    refuses a definition where it is not, rather than let every screen
    discover the inconsistency one request at a time.
    """

    reference: str
    available: tuple[Language, ...]

    def codes(self) -> tuple[str, ...]:
        return tuple(language.code for language in self.available)

    def is_available(self, code: str | None) -> bool:
        return code is not None and code in self.codes()


def load_languages_yaml(path: Path = DEFAULT_LANGUAGES) -> Languages:
    """
    Load `languages.yml`. A missing key names which one and where,
    the same discipline every hand-written definition loader in this
    package already holds.
    """

    data = _read_yaml(path, "language definition")

    if not isinstance(data, dict):
        raise ValueError(f"language definition must contain a mapping: {path}")

    for field in ("reference", "languages"):
        if field not in data:
            raise ValueError(f"language definition {path} is missing: {field}")

    entries = data["languages"]

    if not isinstance(entries, list) or not entries:
        raise ValueError(
            f"language definition {path}: languages must be a non-empty list"
        )

    available: list[Language] = []

    for index, entry in enumerate(entries):
        label = f"language definition {path}: languages[{index}]"

        if not isinstance(entry, dict):
            raise ValueError(f"{label} must be a mapping")

        missing = [field for field in ("code", "name") if field not in entry]

        if missing:
            raise ValueError(f"{label} is missing: {', '.join(missing)}")

        available.append(
            Language(
                code=str(entry["code"]),
                name=str(entry["name"]),
                flag=_flag_uri(path, entry.get("flag"), label),
            )
        )

    codes = [language.code for language in available]

    if len(set(codes)) != len(codes):
        raise ValueError(f"language definition {path} declares a code twice")

    reference = str(data["reference"])

    if reference not in codes:
        raise ValueError(
            f"language definition {path}: reference {reference!r} is not "
            f"one of the declared languages ({', '.join(codes)})"
        )

    return Languages(reference=reference, available=tuple(available))


def load_catalogs(
    languages: Languages, root: Path = DEFAULT_CATALOGS
) -> dict[str, dict[str, str]]:
    """
    Every declared language's messages, flattened to dotted keys.

    **One directory per language, one file per screen.**
    `catalogs/<code>/<namespace>.yml` holds nested mappings; the file
    stem is the key's first segment, so `catalogs/fr/console.yml`'s
    `cartouche: {title: …}` is `console.cartouche.title`. A screen's
    messages then live in one file a translator can read top to
    bottom, rather than scattered through one catalog every screen
    shares.

    Values must be strings. A number or a boolean in a catalog is
    almost always a YAML quoting slip (`yes` read as `True`), and is
    refused here rather than rendered as `True` on a page.
    """

    catalogs: dict[str, dict[str, str]] = {}

    for code in languages.codes():
        directory = root / code

        if not directory.is_dir():
            raise ValueError(f"no catalog directory for language {code!r}: {directory}")

        messages: dict[str, str] = {}

        for path in sorted(directory.glob("*.yml")):
            data = _read_yaml(path, "message catalog")

            if not isinstance(data, dict):
                raise ValueError(f"message catalog must contain a mapping: {path}")

            _flatten(data, path.stem, messages, path)

        catalogs[code] = messages

    return catalogs


def _flatten(
    data: dict[Any, Any], prefix: str, into: dict[str, str], path: Path
) -> None:
    for key, value in data.items():
        dotted = f"{prefix}.{key}"

        if isinstance(value, dict):
            _flatten(value, dotted, into, path)
        elif isinstance(value, str):
            into[dotted] = value
        else:
            raise ValueError(
                f"message catalog {path}: {dotted} must be a string, "
                f"not {type(value).__name__} (quote it in YAML)"
            )


_SHIPPED_FLAGS = Path(__file__).resolve().parent / "definitions" / "flags"


def _flag_uri(definition: Path, flag: Any, label: str) -> str:
    """
    The declared flag file, beside the definition under `flags/`, as a
    `data:image/svg+xml` URI. A declared flag that does not exist is
    refused here, at load time, rather than shown as a broken image.
    """

    if flag is None:
        return ""

    name = str(flag)

    if "/" in name or "\\" in name or not name.endswith(".svg"):
        raise ValueError(f"{label}: flag must be an .svg file name, not {name!r}")

    # Beside the definition first; a definition copied into a
    # configuration directory (ADR-0017 § 1) keeps the shipped flags.
    file = definition.parent / "flags" / name
    if not file.is_file():
        file = _SHIPPED_FLAGS / name

    if not file.is_file():
        raise ValueError(f"{label}: flag file not found: {file}")

    encoded = base64.b64encode(file.read_bytes()).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


def _read_yaml(path: Path, what: str) -> Any:
    with path.open("r", encoding="utf-8") as stream:
        try:
            return yaml.safe_load(stream)
        except yaml.YAMLError as error:
            raise ValueError(f"{what} {path} is not valid YAML: {error}") from error
