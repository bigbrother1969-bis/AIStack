from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache

from aistack.i18n.catalog import Languages, load_catalogs, load_languages_yaml


@dataclass(frozen=True)
class Translator:
    """
    One interface language's messages — what a screen calls `t`.

    Called with a dotted key, it returns that message in `lang`;
    called with a key and keyword arguments, it fills the message's
    named placeholders (`str.format`, so a literal brace in a message
    is written `{{` in the catalog).

    **A key missing from `lang` falls back to the reference language;
    a key missing from the reference too raises `KeyError`.** The
    first is a translation not yet written, which the governed suite
    already refuses to let reach a release
    (`tests/unit/i18n/test_the_real_catalogs.py`), so the fallback only
    ever covers a catalog edited by hand on a running host. The second
    is a screen asking for a message nobody wrote — a defect, stated
    rather than rendered as an empty string (`FDN-0003` Article 12).

    Plain text in, plain text out: a message never carries markup, and
    whatever inserts it into HTML escapes it, exactly as it already
    escapes every other piece of declared text.
    """

    lang: str
    reference: str
    messages: Mapping[str, str]
    reference_messages: Mapping[str, str]

    def __call__(self, key: str, **params: object) -> str:
        template = self.messages.get(key)

        if template is None:
            template = self.reference_messages.get(key)

        if template is None:
            raise KeyError(f"no message {key!r} in any interface catalog")

        return template.format(**params)

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
    """
    The translator for `lang`, or for the reference language when
    `lang` is `None` or not a declared language — a screen asked for
    an unknown language gets the reference, never an error page.
    """

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
