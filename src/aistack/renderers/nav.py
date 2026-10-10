from __future__ import annotations

from aistack.i18n import Languages, Translator
from aistack.renderers.text import escape_text

# ADR-0010. The navigation strip every console-served page carries: back to
# the console, the Settings link and the language switch. Shared rather than
# copied into each renderer so every page shows the same switch in the same
# place; each page appends `PAGE_NAV_STYLE` to its own `_STYLE`.


# Where the web application writes who is signed in (ADR-0013 § 7). An HTML
# comment, so a generated file opened from disk shows nothing there.
SESSION_MARKER = "<!--aistack:session-->"
# Inside every form that changes something: the session's CSRF token
# (ADR-0014 § 3). Where Settings shows profile, sessions and sign-in journal
# (ADR-0014 § 6).
CSRF_MARKER = "<!--aistack:csrf-->"
SETTINGS_MARKER = "<!--aistack:settings-->"


def render_page_nav(
    t: Translator,
    languages: Languages,
    current: str,
    *,
    back_to_console: bool = True,
    console_base_url: str = "",
    extra_query: str = "",
) -> str:
    """Back-to-console link, Settings link and language switch for a page in `current`.

    `back_to_console` is `False` only on the console itself. The back link
    carries `?lang=` so it keeps the language.

    Each language shows its flag with its own name ("English", not
    "Anglais") as alt text and tooltip: a flag names a country, not a
    language. Switch links carry only `?lang=`, relative to the current page.

    `console_base_url` prefixes the console and Settings links for a caller
    served from another origin; empty keeps them relative. `extra_query` is
    appended, already encoded, after each switch's `?lang=<code>`, e.g. so
    `/node` keeps its `iri` when the language changes.
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
    """A language's flag with its name as alt text, or the name when it has no flag.

    `escaped_name` must already be escaped.
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
