from __future__ import annotations

from aistack.config import configured

import base64
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

# ADR-0010. Shipped beside this module and included as package data.
DEFAULT_LANGUAGES = configured(Path(__file__).resolve().parent / "definitions" / "languages.yml")
DEFAULT_CATALOGS = Path(__file__).resolve().parent / "catalogs"


@dataclass(frozen=True)
class Language:
    """One interface language, as `languages.yml` declares it.

    `flag` is a `data:` URI so pages stay single files; empty when no flag
    is declared, and the switch then shows `name`.
    """

    code: str
    name: str
    flag: str = ""


@dataclass(frozen=True)
class Languages:
    """The declared interface languages; `reference` is always one of `available`."""

    reference: str
    available: tuple[Language, ...]

    def codes(self) -> tuple[str, ...]:
        return tuple(language.code for language in self.available)

    def is_available(self, code: str | None) -> bool:
        return code is not None and code in self.codes()


def load_languages_yaml(path: Path = DEFAULT_LANGUAGES) -> Languages:
    """Load `languages.yml`; a missing key is reported with its location."""

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
    """Every declared language's messages, flattened to dotted keys.

    `catalogs/<code>/<namespace>.yml` holds nested mappings and the file stem
    is the first key segment: `console.yml`'s `cartouche: {title: …}` becomes
    `console.cartouche.title`.

    Values must be strings: a number or boolean is almost always a YAML
    quoting slip (`yes` read as `True`) and is refused.
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
    """The declared flag file under `flags/` as a `data:image/svg+xml` URI.

    A missing flag file is refused at load time rather than shown broken.
    """

    if flag is None:
        return ""

    name = str(flag)

    if "/" in name or "\\" in name or not name.endswith(".svg"):
        raise ValueError(f"{label}: flag must be an .svg file name, not {name!r}")

    # Beside the definition first; a definition copied into a configuration
    # directory (ADR-0017 § 1) falls back to the shipped flags.
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
