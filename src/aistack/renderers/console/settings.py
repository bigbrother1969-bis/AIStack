from __future__ import annotations

from aistack.i18n import Languages, default_languages, translator_for
from aistack.renderers.assets import LOCKUP_DATA_URI, MARK_DATA_URI
from aistack.renderers.nav import PAGE_NAV_STYLE, SETTINGS_MARKER, render_page_nav
from aistack.renderers.text import escape_text


def render_settings_html(
    lang: str | None = None,
    languages: Languages | None = None,
    saved: bool = False,
) -> str:
    """
    The console's Settings page — ADR-0010, the owner's own decision of
    2026-09-27 ("une section paramètres de la console").

    One setting in this version: the interface language, remembered
    per browser. The form submits with `GET` to `/settings?lang=…` —
    the same request a language link makes — so choosing a language
    here and following a switch link are one mechanism, not two, and
    the server sets the cookie the same way for both. `saved` is
    `True` when this very request is the one that chose the language,
    and shows a confirmation.

    Nothing here pretends a setting that does not exist yet: users,
    profiles and a per-user language arrive with their own version and
    are added to this page then, not announced on it now.

    Pure, like every renderer in this package — same arguments,
    byte-identical output.
    """

    t = translator_for(lang)
    declared = languages if languages is not None else default_languages()

    options = "\n".join(
        f'      <label class="choice" lang="{language.code}">'
        f'<input type="radio" name="lang" value="{language.code}"'
        f'{" checked" if language.code == t.lang else ""} '
        f'title="{escape_text(t("settings.tooltip.language", name=language.name))}"> '
        f"{_flag(language.flag)}{escape_text(language.name)}</label>"
        for language in declared.available
    )

    confirmation = (
        f'  <p class="saved" role="status">{escape_text(t("settings.language.saved"))}</p>\n'
        if saved
        else ""
    )

    return f"""<!doctype html>
<html lang="{t.lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape_text(t("settings.page_title"))}</title>
<link rel="icon" href="{MARK_DATA_URI}">
<style>
{_STYLE}
{PAGE_NAV_STYLE}
</style>
</head>
<body>
{render_page_nav(t, declared, t.lang)}
<header>
  <a href="/console.html" title="{escape_text(t("settings.tooltip.lockup"))}"><img class="lockup" src="{LOCKUP_DATA_URI}" alt="{escape_text(t("console.lockup_alt"))}"></a>
</header>
<main class="settings">
  <h1>{escape_text(t("settings.title"))}</h1>
  <p class="intro">{escape_text(t("settings.intro"))}</p>
{confirmation}  <section class="setting">
    <form method="get" action="/settings">
    <fieldset>
      <legend>{escape_text(t("settings.language.heading"))}</legend>
{options}
    </fieldset>
    <button type="submit" title="{escape_text(t("settings.tooltip.save"))}">{escape_text(t("settings.language.save"))}</button>
    </form>
    <p class="hint">{escape_text(t("settings.language.hint"))}</p>
  </section>
  {SETTINGS_MARKER}
  <a class="back" href="/console.html" title="{escape_text(t("common.tooltip.back_to_console"))}">{escape_text(t("settings.back"))}</a>
</main>
</body>
</html>
"""


def _flag(flag: str) -> str:
    """The language's flag beside its name; decorative here, the name is written out."""

    if not flag:
        return ""

    return f'<img class="flag" src="{flag}" alt="" width="24" height="16">'


# Same palette and type as the console itself (see
# `aistack.renderers.console.html._STYLE`, 2026-09-26): this page is
# reached from the console and returns to it, and must read as part
# of it.
_STYLE = """\
:root { color-scheme: light; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
    Helvetica, Arial, sans-serif;
  max-width: 900px; margin: 2rem auto;
  color: #1f2933; background: #f7f9fc; padding: 0 1rem;
}
header { text-align: center; margin-bottom: 2rem; }
.lockup { max-width: 220px; width: 100%; height: auto; }
.settings h1 {
  font-family: Georgia, "Times New Roman", Times, serif; font-weight: normal;
  color: #16335c; font-size: 1.6rem; margin: 0 0 .3rem;
}
.intro { color: #5b6b7d; margin: 0 0 1.2rem; }
.saved {
  background: #e4f3ea; border: 1px solid #1f6d43; color: #1f6d43;
  border-radius: 8px; padding: .6rem .9rem; margin: 0 0 1rem;
}
.setting {
  background: #ffffff; border: 1px solid #dde4ed; border-radius: 8px;
  padding: 1rem 1.2rem; margin-bottom: 1.2rem;
}
fieldset { border: 0; padding: 0; margin: 0 0 .8rem; }
legend {
  font-family: Georgia, "Times New Roman", Times, serif; color: #16335c;
  font-size: 1.05rem; margin-bottom: .6rem; padding: 0;
}
.choice {
  display: flex; align-items: center; gap: .5rem; min-height: 44px;
  font-size: .95rem;
}
.choice input { width: 18px; height: 18px; accent-color: #16335c; }
.choice .flag { opacity: 1; box-shadow: 0 0 0 1px #dde4ed; }
button {
  min-height: 44px; padding: 0 1.2rem; border: 0; border-radius: 8px;
  background: #16335c; color: #ffffff; font-size: .95rem; cursor: pointer;
}
.hint { color: #5b6b7d; font-size: .85rem; margin: .8rem 0 0; }
.back { color: #16335c; text-decoration: none; font-size: .9rem; }
.back:hover { text-decoration: underline; }
.auth-settings {
  background: #ffffff; border: 1px solid #dde4ed; border-radius: 8px;
  padding: 1rem 1.2rem; margin-bottom: 1.2rem; overflow-x: auto;
}
.auth-settings h2 {
  font-family: Georgia, "Times New Roman", Times, serif; color: #16335c;
  font-size: 1.05rem; font-weight: normal; margin: 0 0 .6rem;
}
.auth-settings table { border-collapse: collapse; width: 100%; font-size: .85rem; }
.auth-settings th, .auth-settings td {
  text-align: left; padding: .35rem .5rem; border-bottom: 1px solid #eef1f5; vertical-align: top;
}
.auth-settings th { color: #5b6b7d; font-weight: 600; }
.auth-settings button { min-height: 32px; padding: 0 .7rem; font-size: .8rem; }\
"""
