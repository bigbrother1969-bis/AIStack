"""
The console's three reading pages (2026-10-03): help, legal notice,
licence and sources — reached from the console's left column, served
by the console in the visitor's language, every text from the
catalogs and every publisher detail from the declared
`ConsoleIdentity`. Pure, like every renderer in this package.
"""

from __future__ import annotations

from aistack.console.identity import ConsoleIdentity, ContainerImage
from aistack.i18n import Languages, Translator, default_languages, translator_for
from aistack.renderers.assets import LOCKUP_DATA_URI, MARK_DATA_URI
from aistack.renderers.console.settings import _STYLE as SETTINGS_STYLE
from aistack.renderers.nav import PAGE_NAV_STYLE, render_page_nav
from aistack.renderers.text import escape_text

HELP_PATH = "/help"
LEGAL_PATH = "/legal"
LICENSE_PATH = "/license"
MANUAL_PATH = "/help/manual"

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
.reading .manual-link {
  display: inline-block; margin: .2rem 0 1rem; padding: .5rem 1rem; border-radius: 6px;
  background: #16335c; color: #fff; text-decoration: none;
}
.reading .manual-link:hover { filter: brightness(1.15); }
.manual h1 { margin-top: 0; }
.manual h2 { border-top: 1px solid #dde4ed; padding-top: 1rem; margin-top: 2rem; }
.manual h3 { font-size: 1rem; color: #16335c; margin: 1.2rem 0 .3rem; }
.manual ul, .manual ol { line-height: 1.55; padding-left: 1.4rem; }
.manual table { border-collapse: collapse; margin: .6rem 0 1rem; font-size: .92rem; width: 100%; }
.manual th, .manual td { border: 1px solid #dde4ed; padding: .35rem .6rem; text-align: left; vertical-align: top; }
.manual th { background: #f3f6fa; }
.manual pre { background: #f3f6fa; border: 1px solid #dde4ed; border-radius: 6px; padding: .6rem .8rem; overflow-x: auto; }
.manual code { font-size: .88em; }
.manual nav.toc { background: #fff; border: 1px solid #dde4ed; border-radius: 8px; padding: .4rem 1.2rem; margin: 1rem 0 1.5rem; }
.manual nav.toc ul { margin: .3rem 0; }
.manual nav.toc li.sub { margin-left: 1.2rem; font-size: .92rem; }
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
            f'  <a class="manual-link" href="{MANUAL_PATH}?lang={t.lang}" '
            f'title="{escape_text(t("console.tooltip.manual"))}">{escape_text(t("console.help.manual_link"))}</a>',
            *(
                _section(t(f"console.help.{topic}_heading"), escape_text(t(f"console.help.{topic}_text")))
                for topic in ("health", "badges", "screens", "language")
            ),
        ]
    )

    return _page(t, declared, "console.help.page_title", body)


def render_manual_html(lang: str | None = None, languages: Languages | None = None) -> str:
    """The user manual, in the reader's language (the reference
    language's text when a language has none), with its contents."""

    from aistack.manual import manual_source
    from aistack.renderers.markdown import render

    t = translator_for(lang)
    declared = languages if languages is not None else default_languages()
    html, headings = render(manual_source(t.lang, declared.reference))

    entries = "".join(
        f'<li class="{"sub" if heading.level == 3 else ""}"><a href="#{heading.anchor}" '
        f'title="{escape_text(t("console.tooltip.manual_section"))}">{escape_text(heading.text)}</a></li>'
        for heading in headings
        if heading.level in (2, 3)
    )
    toc = f'<nav class="toc"><h2>{escape_text(t("console.help.manual_contents"))}</h2><ul>{entries}</ul></nav>'
    first_heading_end = html.find("</h1>") + len("</h1>")
    body = (
        f'<div class="manual">{html[:first_heading_end]}{toc}{html[first_heading_end:]}</div>\n'
        f'  <a class="back" href="{HELP_PATH}?lang={t.lang}" title="{escape_text(t("console.tooltip.back_to_help"))}">'
        f'{escape_text(t("console.help.back_to_help"))}</a>'
    )

    return _page(t, declared, "console.help.manual_page_title", body)


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

    if identity.publisher:
        publisher_lines = [
            escape_text(
                t(
                    "console.legal.publisher_text",
                    publisher=identity.publisher,
                    legal_form=identity.legal_form,
                    siren=identity.siren,
                    city=identity.city,
                )
            )
        ]
        if identity.publication_director:
            publisher_lines.append(escape_text(t("console.legal.director", director=identity.publication_director)))
        if identity.contact_url:
            publisher_lines.append(escape_text(t("console.legal.contact", contact_url="\0")).replace("\0", contact))
    else:
        # A private installation (2.0.0-rc1): nobody declared as publisher.
        publisher_lines = [escape_text(t("console.legal.private"))]

    body = "\n".join(
        [
            f'  <h1>{escape_text(t("console.legal.title"))}</h1>',
            _section(t("console.legal.publisher_heading"), *publisher_lines),
            _section(t("console.legal.hosting_heading"), escape_text(t("console.legal.hosting_text"))),
            _section(t("console.legal.data_heading"), escape_text(t("console.legal.data_text"))),
            _section(
                t("console.legal.ip_heading"),
                escape_text(t("console.legal.ip_text", license=identity.license)),
            ),
        ]
    )

    return _page(t, declared, "console.legal.page_title", body)


def _image_section(t: Translator, image: ContainerImage) -> str:
    link = (
        f'<br><a href="{escape_text(image.url)}" rel="noopener" '
        f'title="{escape_text(t("console.tooltip.image", registry=image.registry, name=image.name))}">'
        f"{escape_text(image.registry)} — {escape_text(image.url.removeprefix('https://'))}</a>"
    )
    pull = escape_text(t("console.license.image_pull")) + (
        f"<br><code>docker pull {escape_text(image.name)}:&lt;version&gt;</code>"
    )

    return _section(
        t("console.license.image_heading"),
        escape_text(t("console.license.image_text", registry=image.registry)) + link,
        pull,
    )


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
            *(_image_section(t, image) for image in identity.images),
        ]
    )

    return _page(t, declared, "console.license.page_title", body)
