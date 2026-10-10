"""User interface localization (ADR-0010).

Screens read their words from `catalogs/<code>/` through a `Translator`,
always named `t` so the catalog tests can find every key in use.
`languages.yml` declares the languages and the reference one;
`negotiate_language` picks one per request.

Only the interface is translated. Displayed data (container names,
finding text, AI answers, declared notes) stays in its own language.
"""

from aistack.i18n.catalog import (
    DEFAULT_CATALOGS,
    DEFAULT_LANGUAGES,
    Language,
    Languages,
    load_catalogs,
    load_languages_yaml,
)
from aistack.i18n.localized import missing_languages, pick_localized
from aistack.i18n.negotiation import (
    LANGUAGE_COOKIE,
    LANGUAGE_PARAMETER,
    LanguageChoice,
    language_cookie_header,
    negotiate_language,
    read_cookie,
    with_language,
)
from aistack.i18n.translator import Translator, default_languages, translator_for

__all__ = [
    "DEFAULT_CATALOGS",
    "DEFAULT_LANGUAGES",
    "LANGUAGE_COOKIE",
    "LANGUAGE_PARAMETER",
    "Language",
    "LanguageChoice",
    "Languages",
    "Translator",
    "default_languages",
    "language_cookie_header",
    "load_catalogs",
    "load_languages_yaml",
    "missing_languages",
    "negotiate_language",
    "pick_localized",
    "read_cookie",
    "translator_for",
    "with_language",
]
