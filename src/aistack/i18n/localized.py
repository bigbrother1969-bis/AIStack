from __future__ import annotations

from typing import Any

from aistack.i18n.catalog import Languages


def pick_localized(value: Any, lang: str | None, languages: Languages, label: str) -> str:
    """
    One declared field's text in `lang` — ADR-0010, for a definition
    the owner writes by hand (`console_links.yml`), not a catalog.

    A field is either a plain string, the same in every language (a
    product name like "Selection UI" is not translated), or a mapping
    from language code to text. A mapping must carry the reference
    language — it is the one served when nothing else fits — and may
    only name declared languages, so a typo (`eng:`) is refused rather
    than silently never shown. `lang` absent from the mapping falls
    back to the reference, the same rule a catalog key follows.
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
    """
    The declared languages a localized field does not carry — empty
    for a plain string, which is the same in every language by design.
    Used to hold a real definition to every declared language in the
    governed suite, without making the loader itself refuse a field
    the reference alone can still serve.
    """

    if isinstance(value, str):
        return ()

    if not isinstance(value, dict):
        return languages.codes()

    return tuple(code for code in languages.codes() if code not in value)
