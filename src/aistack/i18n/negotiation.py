from __future__ import annotations

from dataclasses import dataclass

from aistack.i18n.catalog import Languages

# ADR-0010 § Decision. The query parameter a link or the Settings form
# carries (`?lang=en`), and the cookie a browser keeps the choice in.
#
# **Per browser, not per user, until users exist** — the owner's own
# decision, 2026-09-27 ("mémorisé par navigateur" in version 1.2; the
# preference moves to the user's own profile once users do). A cookie
# never crosses from one host name to another, which is why the
# console hands the language to each mini-app in the link itself
# rather than counting on the cookie to follow (same decision).
LANGUAGE_PARAMETER = "lang"
LANGUAGE_COOKIE = "aistack_lang"

# One year: a preference, not a session. `SameSite=Lax` because the
# cookie is only ever read on a top-level navigation to one of this
# host's own pages. Not `Secure`: the same console answers on the LAN
# over plain HTTP (`GIGABYTE:8183`) as well as behind the HTTPS
# reverse proxy, and a language choice is not a secret worth losing
# the first of those two for. Not `HttpOnly` either, for the same
# reason in reverse: nothing needs to hide it from the page.
_COOKIE_MAX_AGE = 365 * 24 * 60 * 60


@dataclass(frozen=True)
class LanguageChoice:
    """
    The language one request is served in, and whether the response
    should remember it — `remember` is `True` only when the request
    itself asked for a language (a link or the Settings form), never
    when it was merely read back from the cookie.
    """

    lang: str
    remember: bool


def negotiate_language(
    requested: str | None, remembered: str | None, languages: Languages
) -> LanguageChoice:
    """
    Pick one request's language, in this order: the language the
    request itself names (`?lang=`), then the one this browser
    remembers (the cookie), then the reference language.

    An unknown code in either place is ignored, not an error — a stale
    cookie from a language later withdrawn, or a hand-typed `?lang=xx`,
    falls through to the next rule instead of breaking the page.

    **Not `Accept-Language`.** Guessing from the browser's own
    preference would serve English to a French-speaking owner whose
    browser happens to be set up in English, with no visible cause —
    the reference language until someone chooses is the choice that
    never surprises anyone.
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
    """
    One cookie's value from a raw `Cookie:` header, or `None`.

    Deliberately not `http.cookies.SimpleCookie`: it drops every
    cookie after the first one it fails to parse, so an unrelated,
    oddly-quoted cookie set by another application on the same host
    would silently cost this one its language.
    """

    if not header:
        return None

    for part in header.split(";"):
        key, separator, value = part.strip().partition("=")

        if separator and key == name:
            return value.strip().strip('"') or None

    return None


def with_language(url: str, lang: str) -> str:
    """
    `url` with `?lang=<lang>` appended — how the console hands the
    current language to a mini-app on another host, where its own
    cookie cannot follow (ADR-0010).

    Leaves an in-page anchor (`#…`) alone, and appends with `&` when
    the URL already carries a query string.
    """

    if url.startswith("#"):
        return url

    base, hash_mark, fragment = url.partition("#")
    separator = "&" if "?" in base else "?"
    return f"{base}{separator}{LANGUAGE_PARAMETER}={lang}{hash_mark}{fragment}"
