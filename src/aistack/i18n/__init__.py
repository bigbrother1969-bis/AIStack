"""
User interface localization — ADR-0010.

Every screen AIStack serves reads its words from `catalogs/<code>/`
through a `Translator` (conventionally named `t` wherever it is used,
which is what lets `tests/unit/i18n/test_the_real_catalogs.py` find
every key a screen asks for). `languages.yml` declares which
languages exist and which one is the reference; `negotiate_language`
decides which one a request is served in.

What is translated is the interface itself — headings, labels,
buttons, the sentences a screen writes around its data. What a screen
*displays* is not: a container's name, a finding's own text, an AI
answer or a declared note stay in the language they were produced in
(ADR-0010 § Scope).
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
