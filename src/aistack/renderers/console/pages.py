"""
The console's three reading pages (2026-10-03): help, legal notice,
licence and sources — reached from the console's left column, served
by the console in the visitor's language, every text from the
catalogs and every publisher detail from the declared
`ConsoleIdentity`. Pure, like every renderer in this package.
"""

from __future__ import annotations

from aistack.console.identity import ConsoleIdentity
from aistack.i18n import Languages, Translator, default_languages, translator_for
from aistack.renderers.assets import LOCKUP_DATA_URI, MARK_DATA_URI
from aistack.renderers.console.settings import _STYLE as SETTINGS_STYLE
from aistack.renderers.nav import PAGE_NAV_STYLE, render_page_nav
from aistack.renderers.text import escape_text

HELP_PATH = "/help"
LEGAL_PATH = "/legal"
LICENSE_PATH = "/license"

_STYLE = """\
.reading h1 {
  font-family: Georgia, "Times New Roman", Times, serif; font-weight: normal;
  color: #16335c; font-size: 1.6rem; margin: 0 0 .8rem;
}
.reading h2 {
  font-family: Georgia, "Times New Roman", Times, serif; font-weight: normal;
  color: #16335c; font-size: 1.15rem; margin: 1.4rem 0 .4rem;
}
.reading p { line-height: 1.55; margin: 0 0 .6rem; }
.reading section {
  background: #ffffff; border: 1px solid #dde4ed; border-radius: 8px;
  padding: .4rem 1.2rem .8rem; margin-bottom: 1rem;
}
.reading a { color: #16335c; }
"""


def _page(t: Translator, declared: Languages, title_key: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="{t.lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape_text(t(title_key))}</title>
<link rel="icon" href="{MARK_DATA_URI}">
<style>
{SETTINGS_STYLE}
{PAGE_NAV_STYLE}
{_STYLE}
</style>
</head>
<body>
{render_page_nav(t, declared, t.lang)}
<header>
  <a href="/console.html" title="{escape_text(t("common.tooltip.back_to_console"))}"><img class="lockup" src="{LOCKUP_DATA_URI}" alt="{escape_text(t("console.lockup_alt"))}"></a>
</header>
<main class="reading">
{body}
  <a class="back" href="/console.html" title="{escape_text(t("common.tooltip.back_to_console"))}">{escape_text(t("common.console.back"))}</a>
</main>
</body>
</html>
"""


def _section(heading: str, *paragraphs: str) -> str:
    inner = "\n".join(f"    <p>{paragraph}</p>" for paragraph in paragraphs)

    return f"  <section>\n    <h2>{escape_text(heading)}</h2>\n{inner}\n  </section>"


def render_help_html(lang: str | None = None, languages: Languages | None = None) -> str:
    t = translator_for(lang)
    declared = languages if languages is not None else default_languages()

    body = "\n".join(
        [
            f'  <h1>{escape_text(t("console.help.title"))}</h1>',
            f'  <p>{escape_text(t("console.help.intro"))}</p>',
            *(
                _section(t(f"console.help.{topic}_heading"), escape_text(t(f"console.help.{topic}_text")))
                for topic in ("health", "badges", "screens", "language")
            ),
        ]
    )

    return _page(t, declared, "console.help.page_title", body)


def render_legal_html(
    identity: ConsoleIdentity, lang: str | None = None, languages: Languages | None = None
) -> str:
    t = translator_for(lang)
    declared = languages if languages is not None else default_languages()
    contact = (
        f'<a href="{escape_text(identity.contact_url)}" rel="noopener" '
        f'title="{escape_text(t("console.tooltip.contact"))}">'
        f"{escape_text(identity.contact_url.removeprefix('https://'))}</a>"
    )

    body = "\n".join(
        [
            f'  <h1>{escape_text(t("console.legal.title"))}</h1>',
            _section(
                t("console.legal.publisher_heading"),
                escape_text(
                    t(
                        "console.legal.publisher_text",
                        publisher=identity.publisher,
                        legal_form=identity.legal_form,
                        siren=identity.siren,
                        city=identity.city,
                    )
                ),
                escape_text(t("console.legal.director", director=identity.publication_director)),
                escape_text(t("console.legal.contact", contact_url="\0")).replace("\0", contact),
            ),
            _section(t("console.legal.hosting_heading"), escape_text(t("console.legal.hosting_text"))),
            _section(t("console.legal.data_heading"), escape_text(t("console.legal.data_text"))),
            _section(
                t("console.legal.ip_heading"),
                escape_text(t("console.legal.ip_text", license=identity.license)),
            ),
        ]
    )

    return _page(t, declared, "console.legal.page_title", body)


def render_license_html(
    identity: ConsoleIdentity, lang: str | None = None, languages: Languages | None = None
) -> str:
    t = translator_for(lang)
    declared = languages if languages is not None else default_languages()

    repositories = "".join(
        f'<br><a href="{escape_text(repository.url)}" rel="noopener" '
        f'title="{escape_text(t("console.tooltip.repository", name=repository.name))}">'
        f"{escape_text(repository.name)} — {escape_text(repository.url.removeprefix('https://'))}</a>"
        for repository in identity.repositories
    )

    body = "\n".join(
        [
            f'  <h1>{escape_text(t("console.license.title"))}</h1>',
            "  <section>",
            f'    <p>{escape_text(t("console.license.text", license=identity.license))}</p>',
            f'    <p><a href="{escape_text(identity.license_url)}" rel="noopener" '
            f'title="{escape_text(t("console.tooltip.license_text"))}">'
            f'{escape_text(t("console.license.license_link", license=identity.license))}</a></p>',
            "  </section>",
            _section(
                t("console.license.sources_heading"),
                escape_text(t("console.license.sources_text")) + repositories,
            ),
        ]
    )

    return _page(t, declared, "console.license.page_title", body)
