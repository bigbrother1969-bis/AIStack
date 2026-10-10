from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache

from aistack.i18n.catalog import Languages, load_catalogs, load_languages_yaml


@dataclass(frozen=True)
class Translator:
    """One interface language's messages; screens call it `t`.

    `t(key, **params)` returns the message in `lang`, filling placeholders
    with `str.format` (a literal brace is written `{{` in the catalog).

    A key missing from `lang` falls back to the reference language; a key
    missing from the reference too raises `KeyError`. Messages are plain
    text; callers escape them when inserting into HTML.
    """

    lang: str
    reference: str
    messages: Mapping[str, str]
    reference_messages: Mapping[str, str]

    def __call__(self, key: str, **params: object) -> str:
        return self.raw(key).format(**params)

    def raw(self, key: str) -> str:
        """The message with placeholders unfilled, for a page whose script fills them.

        Same fallback and `KeyError` as a call.
        """

        template = self.messages.get(key)

        if template is None:
            template = self.reference_messages.get(key)

        if template is None:
            raise KeyError(f"no message {key!r} in any interface catalog")

        return template

    def has(self, key: str) -> bool:
        return key in self.messages or key in self.reference_messages


@lru_cache(maxsize=1)
def default_languages() -> Languages:
    """The declared languages, read once per process."""

    return load_languages_yaml()


@lru_cache(maxsize=1)
def _default_catalogs() -> dict[str, dict[str, str]]:
    return load_catalogs(default_languages())


def translator_for(lang: str | None) -> Translator:
    """Translator for `lang`, or for the reference language when `lang` is unknown."""

    languages = default_languages()
    catalogs = _default_catalogs()
    code = lang if languages.is_available(lang) else languages.reference

    assert code is not None

    return Translator(
        lang=code,
        reference=languages.reference,
        messages=catalogs[code],
        reference_messages=catalogs[languages.reference],
    )
