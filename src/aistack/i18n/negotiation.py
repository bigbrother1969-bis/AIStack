from __future__ import annotations

from dataclasses import dataclass

from aistack.i18n.catalog import Languages

# ADR-0010: the query parameter (`?lang=en`) and the cookie holding the choice.
# The choice is per browser. A cookie does not cross host names, so the
# console passes the language to other hosts in the link itself.
LANGUAGE_PARAMETER = "lang"
LANGUAGE_COOKIE = "aistack_lang"

# One year: a preference, not a session. `SameSite=Lax`: only read on
# top-level navigation. Not `Secure`, because the console also answers over
# plain HTTP on the LAN; not `HttpOnly`, as nothing needs hiding it.
_COOKIE_MAX_AGE = 365 * 24 * 60 * 60


@dataclass(frozen=True)
class LanguageChoice:
    """The language a request is served in, and whether to remember it.

    `remember` is `True` only when the request itself asked for a language,
    never when it was read back from the cookie.
    """

    lang: str
    remember: bool


def negotiate_language(
    requested: str | None, remembered: str | None, languages: Languages
) -> LanguageChoice:
    """Pick a request's language: `?lang=`, then the cookie, then the reference.

    An unknown code in either place is ignored, not an error. Deliberately
    not `Accept-Language`: a browser set up in English would serve English
    to a French-speaking owner with no visible cause.
    """

    if languages.is_available(requested):
        assert requested is not None
        return LanguageChoice(lang=requested, remember=True)

    if languages.is_available(remembered):
        assert remembered is not None
        return LanguageChoice(lang=remembered, remember=False)

    return LanguageChoice(lang=languages.reference, remember=False)


def language_cookie_header(lang: str) -> str:
    """The `Set-Cookie` value that remembers `lang` in this browser."""

    return (
        f"{LANGUAGE_COOKIE}={lang}; Path=/; Max-Age={_COOKIE_MAX_AGE}; "
        f"SameSite=Lax"
    )


def read_cookie(header: str | None, name: str = LANGUAGE_COOKIE) -> str | None:
    """One cookie's value from a raw `Cookie:` header, or `None`.

    Not `http.cookies.SimpleCookie`: it drops every cookie after the first one
    it fails to parse, so another application's odd cookie would lose the language.
    """

    if not header:
        return None

    for part in header.split(";"):
        key, separator, value = part.strip().partition("=")

        if separator and key == name:
            return value.strip().strip('"') or None

    return None


def with_language(url: str, lang: str) -> str:
    """`url` with `?lang=<lang>` appended, to carry the language to another host.

    Leaves an in-page anchor (`#…`) alone and uses `&` when a query exists.
    """

    if url.startswith("#"):
        return url

    base, hash_mark, fragment = url.partition("#")
    separator = "&" if "?" in base else "?"
    return f"{base}{separator}{LANGUAGE_PARAMETER}={lang}{hash_mark}{fragment}"
