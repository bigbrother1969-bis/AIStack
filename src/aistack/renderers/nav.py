from __future__ import annotations

from aistack.i18n import Languages, Translator
from aistack.renderers.text import escape_text

# ADR-0010. The one strip of navigation every page the console serves
# carries: the way back to the console (on every page but the console
# itself), the link to Settings, and a direct switch between the
# declared languages.
#
# **Shared, not duplicated, the same way `escape_text` is.** Each
# renderer in this package keeps its own `_STYLE` and imports nothing
# from another renderer; this module is not a renderer — it is one
# piece of markup three renderers must agree on exactly, since a
# visitor moving from the console to Architecture must find the same
# switch in the same place. Three copies of it would be three places
# for that agreement to drift. Its style travels with it
# (`PAGE_NAV_STYLE`), appended by each page to its own `_STYLE`.


# Where the web application writes who is signed in (`ADR-0013` § 7):
# a comment, so a page served without it — a generated file opened
# straight from disk — shows nothing in its place.
SESSION_MARKER = "<!--aistack:session-->"


def render_page_nav(
    t: Translator,
    languages: Languages,
    current: str,
    *,
    back_to_console: bool = True,
    console_base_url: str = "",
    extra_query: str = "",
) -> str:
    """
    The way back to the console, the Settings link and the language
    switch, for a page served in `current`.

    `back_to_console` is `False` on the console alone: every other page
    it serves (Architecture, the Health cockpit, Settings) is reached
    from it and must lead back to it without the browser's own Back
    button — the owner's finding on the first real use, 2026-09-27. The
    link carries `?lang=`, the same way the console's own links to the
    mini-apps do, so the way back never changes the language.

    Each language is shown by its declared flag (owner's request,
    2026-09-27), with its own name for itself ("English", not
    "Anglais") as the flag's alternative text and tooltip — a flag
    names a country, not a language, and a visitor who cannot read the
    current language can still find theirs. The switch links carry only `?lang=`: relative
    to the page being read, so the same markup works on the console,
    Architecture and the Health cockpit alike, and the server answers
    each with the same page in the other language.

    **`console_base_url`, added 2026-09-30** (`claude/AUDIT-CONSOLE-
    ARCHITECTURE-HEALTH-2026-09-29.md`, constat 5) — empty by default,
    which reproduces the exact markup this function always emitted:
    the console and Settings links stay relative (`/console.html?...`,
    `/settings`), correct only when the caller is served by the same
    process as the console itself (console/architecture/health/
    settings, still true today). A caller served from a different
    process on a different port — `timemachine_ui`, on its own FastAPI
    instance — passes its own console origin here (the same `http://
    GIGABYTE:8183` its five screens already hardcoded before this
    field existed) so both links resolve correctly across the port
    boundary; the language switch itself is untouched by this
    parameter, since it must always stay on the CURRENT page.

    **`extra_query`, added 2026-09-30, same constat** — appended
    verbatim (already encoded by the caller) after each language
    switch's own `?lang=<code>`. Empty by default, so every existing
    caller's switch links are byte-identical to before. `timemachine_
    ui`'s `/node` screen is the one caller that needs this: its
    language switch must keep the `iri` of the node being read, or
    switching language would silently drop the visitor back to an
    unparented `/node` request.
    """

    switches = []

    for language in languages.available:
        name = escape_text(language.name)
        label = language_label(language.flag, name)

        if language.code == current:
            switches.append(
                f'<span class="lang-current" lang="{language.code}" '
                f'title="{name}" aria-current="true">{label}</span>'
            )
        else:
            switches.append(
                f'<a href="?lang={language.code}{extra_query}" hreflang="{language.code}" '
                f'lang="{language.code}" title="{name}">{label}</a>'
            )

    back = (
        f'<a class="console-link" href="{console_base_url}/console.html?lang={current}" '
        f'title="{escape_text(t("common.tooltip.back_to_console"))}">'
        f'{escape_text(t("common.console.back"))}</a>'
        if back_to_console
        else ""
    )

    return (
        f'<nav class="page-nav" aria-label="{escape_text(t("common.language.switch_label"))}">'
        f"{back}"
        f"{SESSION_MARKER}"
        f'<span class="lang-switch">{"".join(switches)}</span>'
        f'<a class="settings-link" href="{console_base_url}/settings" '
        f'title="{escape_text(t("common.settings.tooltip"))}">{escape_text(t("common.settings.link"))}</a>'
        f"</nav>"
    )


def language_label(flag: str, escaped_name: str) -> str:
    """
    What a language switch shows for one language: its flag, with the
    name as the image's alternative text — or the name itself when the
    language declares no flag. `escaped_name` is already escaped.
    """

    if not flag:
        return escaped_name

    return (
        f'<img class="flag" src="{flag}" alt="{escaped_name}" '
        f'width="24" height="16">'
    )


PAGE_NAV_STYLE = """\
.page-nav {
  display: flex; justify-content: flex-end; align-items: center;
  gap: 1rem; font-size: .85rem; margin: 0 0 .8rem;
}
.page-nav a { color: #16335c; text-decoration: none; }
.page-nav a:hover { text-decoration: underline; }
.console-link { margin-right: auto; }
.lang-switch { display: inline-flex; align-items: center; gap: .5rem; }
.lang-switch a, .lang-current { display: inline-flex; line-height: 0; }
.lang-current { font-weight: 600; color: #1f2933; }
.flag {
  width: 24px; height: 16px; border-radius: 2px;
  box-shadow: 0 0 0 1px #dde4ed; opacity: .55;
}
.lang-switch a:hover .flag { opacity: 1; }
.lang-current .flag { opacity: 1; box-shadow: 0 0 0 2px #16335c; }
.settings-link {
  border: 1px solid #dde4ed; border-radius: 6px; padding: .25rem .6rem;
  background: #ffffff;
}\
"""
