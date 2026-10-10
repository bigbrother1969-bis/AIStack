from __future__ import annotations

from typing import Any

from aistack.i18n.catalog import Languages


def pick_localized(value: Any, lang: str | None, languages: Languages, label: str) -> str:
    """Text of one hand-written localized field (e.g. in `console_links.yml`) in `lang`.

    A field is a plain string (same in every language) or a mapping from
    language code to text. A mapping must include the reference language and
    only declared languages, so a typo like `eng:` is refused. A missing
    `lang` falls back to the reference.
    """

    if isinstance(value, str):
        return value

    if not isinstance(value, dict) or not value:
        raise ValueError(
            f"{label} must be a string or a mapping from language code to text"
        )

    unknown = sorted(str(code) for code in value if not languages.is_available(str(code)))

    if unknown:
        raise ValueError(
            f"{label} names undeclared language(s): {', '.join(unknown)}"
        )

    if languages.reference not in value:
        raise ValueError(
            f"{label} is missing the reference language: {languages.reference}"
        )

    for code, text in value.items():
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"{label}.{code} must be non-empty text")

    code = lang if lang in value else languages.reference
    return str(value[code])


def missing_languages(value: Any, languages: Languages) -> tuple[str, ...]:
    """Declared languages a localized field lacks; empty for a plain string.

    Lets tests require every language without making the loader refuse
    a field the reference alone can serve.
    """

    if isinstance(value, str):
        return ()

    if not isinstance(value, dict):
        return languages.codes()

    return tuple(code for code in languages.codes() if code not in value)
