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


def render_page_nav(
    t: Translator,
    languages: Languages,
    current: str,
    *,
    back_to_console: bool = True,
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

    Each language is shown by its own name for itself ("English", not
    "Anglais") — a visitor who cannot read the current language can
    still find theirs. The switch links carry only `?lang=`: relative
    to the page being read, so the same markup works on the console,
    Architecture and the Health cockpit alike, and the server answers
    each with the same page in the other language.
    """

    switches = []

    for language in languages.available:
        name = escape_text(language.name)

        if language.code == current:
            switches.append(
                f'<span class="lang-current" lang="{language.code}" '
                f'aria-current="true">{name}</span>'
            )
        else:
            switches.append(
                f'<a href="?lang={language.code}" hreflang="{language.code}" '
                f'lang="{language.code}">{name}</a>'
            )

    back = (
        f'<a class="console-link" href="/console.html?lang={current}">'
        f'{escape_text(t("common.console.back"))}</a>'
        if back_to_console
        else ""
    )

    return (
        f'<nav class="page-nav" aria-label="{escape_text(t("common.language.switch_label"))}">'
        f"{back}"
        f'<span class="lang-switch">{" · ".join(switches)}</span>'
        f'<a class="settings-link" href="/settings">{escape_text(t("common.settings.link"))}</a>'
        f"</nav>"
    )


PAGE_NAV_STYLE = """\
.page-nav {
  display: flex; justify-content: flex-end; align-items: center;
  gap: 1rem; font-size: .85rem; margin: 0 0 .8rem;
}
.page-nav a { color: #16335c; text-decoration: none; }
.page-nav a:hover { text-decoration: underline; }
.console-link { margin-right: auto; }
.lang-current { font-weight: 600; color: #1f2933; }
.settings-link {
  border: 1px solid #dde4ed; border-radius: 6px; padding: .25rem .6rem;
  background: #ffffff;
}\
"""
