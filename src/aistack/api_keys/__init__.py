"""
API keys entered from Settings (the owner, 2026-10-09): which keys
exist (`api_keys.yml`), where the entered values are kept, and how a
process takes them into its environment.

Every component reads its key from the environment, as it did from
`.env.web`. A value entered in Settings is kept in the data directory,
`secrets/api_keys.json`, readable by AIStack's user only (0600), and
laid over the environment by `apply_to_environ` — at the web
application's start and after each change, at each pass of the vigil,
at the start of the resource-priority monitor. It wins over `.env.web`;
cleared, the `.env.web` value comes back.

A value is never shown again: `state` gives where it comes from and its
last four characters only.
"""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import MutableMapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from aistack.config import configured

SHIPPED = Path(__file__).resolve().parent / "definitions" / "api_keys.yml"
STORE = Path("secrets") / "api_keys.json"

FROM_SETTINGS = "settings"
FROM_ENV_FILE = "env"
ABSENT = "absent"


@dataclass(frozen=True)
class ApiKey:
    name: str
    title: dict[str, str]
    used_by: dict[str, str]
    applies: dict[str, str]
    secret: bool = True
    test: str = ""
    procedure: tuple[tuple[str, tuple[str, ...]], ...] = ()
    prerequisite: str = ""
    suggested: str = ""

    def steps(self, lang: str, host: str = "") -> list[str]:
        """The procedure in `lang` (else the first language), `{host}` filled."""

        found = dict(self.procedure)
        lines = found.get(lang) or (self.procedure[0][1] if self.procedure else ())
        return [line.replace("{host}", host or "localhost") for line in lines]

    def text(self, field: dict[str, str], lang: str) -> str:
        return field.get(lang) or next(iter(field.values()), self.name)


def load_api_keys(path: Path | None = None) -> list[ApiKey]:
    source = path if path is not None else configured(SHIPPED)
    data = yaml.safe_load(source.read_text(encoding="utf-8")) or {}
    keys = []
    for raw in data.get("keys") or []:
        if not isinstance(raw, dict) or not raw.get("name"):
            raise ValueError(f"{source}: a key names no environment variable")

        def text(value: Any, fallback: str) -> dict[str, str]:
            if isinstance(value, dict):
                return {str(k): str(v) for k, v in value.items()}
            return {"fr": str(value or fallback), "en": str(value or fallback)}

        keys.append(
            ApiKey(
                name=str(raw["name"]),
                title=text(raw.get("title"), str(raw["name"])),
                used_by=text(raw.get("used_by"), ""),
                applies=text(raw.get("applies"), ""),
                secret=bool(raw.get("secret", True)),
                test=str(raw.get("test") or ""),
                procedure=tuple(
                    (str(lang), tuple(str(line) for line in lines or ()))
                    for lang, lines in (raw.get("procedure") or {}).items()
                ),
                prerequisite=str(raw.get("prerequisite") or ""),
                suggested=str(raw.get("suggested") or ""),
            )
        )
    return keys


def read_store(generated_dir: Path, store: Path = STORE) -> dict[str, str]:
    try:
        data = json.loads((generated_dir / store).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {str(k): str(v) for k, v in data.items() if isinstance(v, str) and v} if isinstance(data, dict) else {}


def write_value(generated_dir: Path, name: str, value: str | None, store: Path = STORE) -> None:
    """Keep `value` for `name` (None or empty: forget it), atomically, mode 0600;
    `store` is another file of the same kind (the installation assistant's
    sign-in secrets, `aistack.instance.setup_wizard`)."""

    stored = read_store(generated_dir, store)
    if value:
        stored[name] = value
    else:
        stored.pop(name, None)
    path = generated_dir / store
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.stem}.")
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(stored, stream, indent=2, sort_keys=True)
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


# What the environment held before a Settings value was laid over it,
# so a value cleared in Settings gives `.env.web`'s back.
_ORIGINAL: dict[str, str | None] = {}


def apply_to_environ(
    generated_dir: Path, keys: list[ApiKey] | None = None, environ: MutableMapping[str, str] | None = None
) -> None:
    env = os.environ if environ is None else environ
    stored = read_store(generated_dir)
    for key in keys if keys is not None else load_api_keys():
        if key.name in stored:
            _ORIGINAL.setdefault(key.name, env.get(key.name))
            env[key.name] = stored[key.name]
        elif key.name in _ORIGINAL:
            original = _ORIGINAL.pop(key.name)
            if original is None:
                env.pop(key.name, None)
            else:
                env[key.name] = original


def state(key: ApiKey, generated_dir: Path, environ: MutableMapping[str, str] | None = None) -> tuple[str, str]:
    """(where the value comes from, what may be shown of it)."""

    env = os.environ if environ is None else environ
    stored = read_store(generated_dir)
    if key.name in stored:
        source, value = FROM_SETTINGS, stored[key.name]
    else:
        original = _ORIGINAL.get(key.name, env.get(key.name)) if key.name in _ORIGINAL else env.get(key.name)
        if not original:
            return ABSENT, ""
        source, value = FROM_ENV_FILE, original
    return source, value if not key.secret else ("…" + value[-4:] if len(value) > 8 else "…")
