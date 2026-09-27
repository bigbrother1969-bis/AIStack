"""
The real catalogs under `src/aistack/i18n/catalogs/` — ADR-0010.

Not fixtures: these are the words every screen actually shows. Three
facts are checked here rather than trusted, because each one fails
silently in a browser:

- every language carries exactly the reference language's keys — a
  key missing from English would quietly render in French, a key
  present only in English would never render at all;
- every translation of a message carries the same named placeholders
  — `{count}` renamed `{number}` in one language raises on that
  language's page only;
- every key a screen asks for (`t("…")` in `src/aistack/` and in the
  four mini-apps' `app.py` and templates) exists — otherwise the
  screen raises `KeyError` the first time it is rendered, which for a
  mini-app outside the governed suite means on GIGABYTE, in front of
  the owner.
"""

from __future__ import annotations

import re
import string
from pathlib import Path

from aistack.i18n import DEFAULT_CATALOGS, load_catalogs, load_languages_yaml

REPO_ROOT = Path(__file__).resolve().parents[3]

# The four mini-apps live beside `src/`, not in it (decision #9,
# 2026-08-29: fastapi stays out of the governed venv). Their `app.py`
# cannot be imported by this suite, but their text can be read.
_UI_DIRECTORIES = (
    "selection_ui",
    "priority_ui",
    "network_discovery_ui",
    "troubleshooting_assistant_ui",
    "timemachine_ui",
)

# `t("a.b")` / `t('a.b')` — or `t.raw(...)`, the unfilled form a
# page's own script completes — in Python and in Jinja alike. Screens name
# their translator `t` so this one pattern finds every lookup; a key
# built at runtime (a domain name, a bucket) goes through an explicit
# mapping with its own test instead.
_KEY_USE = re.compile(r"""\bt(?:\.raw)?\(\s*["']([A-Za-z0-9_.\-]+)["']""")


def catalogs() -> dict[str, dict[str, str]]:
    return load_catalogs(load_languages_yaml())


def placeholders(message: str) -> set[str]:
    return {
        field for _, field, _, _ in string.Formatter().parse(message) if field
    }


def used_keys() -> dict[str, set[Path]]:
    files = list((REPO_ROOT / "src" / "aistack").rglob("*.py"))

    for directory in _UI_DIRECTORIES:
        root = REPO_ROOT / directory
        files.extend(root.glob("*.py"))
        files.extend((root / "templates").glob("*.html"))

    found: dict[str, set[Path]] = {}

    for path in files:
        for key in _KEY_USE.findall(path.read_text(encoding="utf-8")):
            found.setdefault(key, set()).add(path.relative_to(REPO_ROOT))

    return found


def test_every_declared_language_has_a_catalog_directory():
    for code in load_languages_yaml().codes():
        assert (DEFAULT_CATALOGS / code).is_dir(), code


def test_every_language_carries_exactly_the_reference_keys():
    languages = load_languages_yaml()
    loaded = catalogs()
    reference = set(loaded[languages.reference])

    for code in languages.codes():
        keys = set(loaded[code])

        assert keys - reference == set(), f"{code}: keys the reference lacks"
        assert reference - keys == set(), f"{code}: untranslated keys"


def test_every_translation_keeps_the_reference_placeholders():
    languages = load_languages_yaml()
    loaded = catalogs()

    for key, message in loaded[languages.reference].items():
        for code in languages.codes():
            assert placeholders(loaded[code][key]) == placeholders(message), (
                f"{code}: {key} does not carry the same placeholders"
            )


def test_every_key_a_screen_asks_for_exists():
    languages = load_languages_yaml()
    reference = catalogs()[languages.reference]
    missing = {
        key: sorted(str(path) for path in paths)
        for key, paths in used_keys().items()
        if key not in reference
    }

    assert missing == {}


def test_no_message_is_left_empty():
    for code, messages in catalogs().items():
        for key, message in messages.items():
            assert message.strip(), f"{code}: {key} is empty"
