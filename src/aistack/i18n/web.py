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
    """
    Everything a web screen needs to answer one request in the right
    language — ADR-0010, for the four mini-apps.

    **Framework-free on purpose** (roadmap R5, 2026-09-27: logic in
    `src/`, tested; web layers thin). A mini-app reads `?lang=` and its
    cookie off its own request object, hands both here, puts
    `context()` into its template, and — only when `cookie` is not
    `None` — adds it as a `Set-Cookie` header. Nothing here imports
    FastAPI, so all of it is covered by the governed suite even though
    the mini-apps themselves are not (decision #9, 2026-08-29).
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
    """
    Negotiate one request's language (ADR-0010 § 3) and build what the
    page needs from it: its translator, its language switch, and the
    cookie to set when the request itself chose the language — how the
    language a visitor picked on the console, carried here in the link
    (`?lang=`), is remembered by this mini-app for its own host.
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
