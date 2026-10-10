from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aistack.i18n.catalog import Languages
from aistack.i18n.negotiation import language_cookie_header, negotiate_language
from aistack.i18n.translator import Translator, default_languages, translator_for


@dataclass(frozen=True)
class LanguageOption:
    """One entry of a page's language switch."""

    code: str
    name: str
    current: bool
    flag: str = ""


@dataclass(frozen=True)
class PageLanguage:
    """What a web screen needs to answer one request in the right language (ADR-0010).

    Framework-free: the caller passes `?lang=` and the cookie, puts
    `context()` into its template and sets `cookie` as `Set-Cookie` when it
    is not `None`.
    """

    lang: str
    t: Translator
    options: tuple[LanguageOption, ...]
    cookie: str | None

    def context(self) -> dict[str, Any]:
        """The three names every localized template reads."""

        return {"lang": self.lang, "t": self.t, "language_options": self.options}


def page_language(
    requested: str | None,
    remembered: str | None,
    languages: Languages | None = None,
) -> PageLanguage:
    """Negotiate a request's language (ADR-0010 § 3) and build its `PageLanguage`.

    `cookie` is set only when the request itself chose the language
    (`?lang=`), so a choice made on the console is remembered here too.
    """

    declared = languages if languages is not None else default_languages()
    choice = negotiate_language(requested, remembered, declared)

    return PageLanguage(
        lang=choice.lang,
        t=translator_for(choice.lang),
        options=tuple(
            LanguageOption(
                code=language.code,
                name=language.name,
                current=language.code == choice.lang,
                flag=language.flag,
            )
            for language in declared.available
        ),
        cookie=language_cookie_header(choice.lang) if choice.remember else None,
    )
