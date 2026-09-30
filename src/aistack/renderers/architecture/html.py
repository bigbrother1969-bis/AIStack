from __future__ import annotations

import json
from pathlib import Path

from aistack.architecture.beszel_reading import BeszelSystemReading
from aistack.architecture.dependency_graph import DependencyGraph
from aistack.architecture.http_probe_reading import HttpProbeReading
from aistack.architecture.topology_definition import InfrastructureTopologyDefinition
from aistack.architecture.views import FULL_VIEW, ArchitectureView
from aistack.i18n import Languages, Translator, default_languages, translator_for
from aistack.renderers.assets import MARK_DATA_URI
from aistack.renderers.nav import PAGE_NAV_STYLE, render_page_nav
from aistack.renderers.architecture.dependency_mermaid import render_dependency_mermaid
from aistack.renderers.architecture.icons import load_icon_data_uri
from aistack.renderers.architecture.mermaid import escape_text, render_mermaid

# The extra `<select>` entry `render_html` adds when a `DependencyGraph`
# carries at least one project — a plain constant rather than a name
# derived from anything, since nothing about a dependency view is a
# category or `FULL_VIEW` (`views.py` never produces this name, so
# there is no real collision to guard beyond the defensive check
# `render_html` itself makes before adding it).
_DEPENDENCY_VIEW_NAME = "dependencies"

_VENDOR_PATH = Path(__file__).resolve().parent / "vendor" / "mermaid.min.js"

# A vendored `<script>` block is embedded verbatim between real
# `<script>` tags. A browser ends a script element at the first
# literal `</script` it finds in the markup, regardless of where that
# text sits in the JavaScript source — inside a string, a comment, a
# regex literal, anywhere. `vendor/PROVENANCE.md` records that
# mermaid@11.17.2's own bundle carries no such substring; `render_html`
# checks it again at render time rather than trusting that a future
# `npm install mermaid@<newer>` preserves it — an upgrade that ever
# introduces one would otherwise produce a page that silently renders
# nothing, with no error naming why.
_SCRIPT_TERMINATOR = "</script"


def load_vendored_mermaid_js() -> str:
    """
    Read the vendored mermaid.js bundle `render_html` embeds inline.

    **Vendored, not CDN-linked — decided with the owner, 2026-09-10.**
    `architecture.html` is meant to open and render with no network
    access at all, including on a machine with no route to the
    homelab's own network. A `<script src="https://...">` tag would
    make every future viewing depend on a CDN staying reachable; a
    vendored copy makes the file the same artifact tomorrow as today,
    at the cost of a multi-megabyte inline `<script>` block and an
    explicit upgrade step (`vendor/PROVENANCE.md`) whenever a newer
    mermaid.js is wanted.

    **Read from disk beside this module** — the same
    `Path(__file__).resolve()`-relative convention
    `resource_priority_monitor.py`'s `DEFAULT_DEFINITION` already
    uses, not `importlib.resources`. Packaging this file for a real,
    non-editable install needs exactly what that convention needs:
    `[tool.setuptools.package-data]` in `pyproject.toml` — added the
    same patch that added this module, after a real (non-editable)
    `pip install .` was found to carry no `.yml`/`.js` data file at
    all (`docs/03-governance/GOV-0002-Open-State-Register.md`,
    `GOV-0002/OS-056`).
    """

    return _VENDOR_PATH.read_text(encoding="utf-8")


def render_html(
    views: tuple[ArchitectureView, ...],
    topology: InfrastructureTopologyDefinition | None = None,
    beszel_readings: tuple[BeszelSystemReading, ...] = (),
    dependency_graph: DependencyGraph | None = None,
    cmdb_readings: tuple[HttpProbeReading, ...] = (),
    lang: str | None = None,
    languages: Languages | None = None,
) -> str:
    """
    Wrap every view of an `ArchitectureGraph` into one self-contained
    HTML page — a `<select>` switches which view's Mermaid diagram is
    rendered, client-side, into the page.

    This is what names the Kernel Runtime `render` operation
    (`docs/99-meta/roadmap/Kernel-Runtime-Roadmap.md`) for the first
    time: this function and its sibling `render_mermaid` are the
    first tenants of the `renderers/` package, empty since it was
    scaffolded.

    **Pure — no wall clock.** Nothing here reads `datetime.now()`; the
    page is a function of `views` alone, so the same graph always
    renders to byte-identical output — the determinism
    `ENG-TEST-0002` asks of everything this heritage generates.
    `ArchitectureHtmlArtifactGenerator`
    (`aistack/generators/architecture/html_artifact.py`) is what
    stamps *when* a copy was produced, in the history filename
    (`write_artifact_with_history`) — not in the content itself, which
    would otherwise differ on every run for no reason a diff could
    explain.

    **Expects `views[0]` to be the full view.** `build_all_views`
    documents exactly that order — `FULL_VIEW` first, then one per
    category — and this relies on it rather than re-deriving it, but
    checks rather than assumes silently: an empty or differently
    ordered sequence raises, naming what was expected.

    **`topology` is optional, added 2026-09-12**
    (`claude/PLAN-J11-CONSOLE-2026-09-11.md` §10) — external network
    nodes (OVH, Cloudflare, the Freebox...) and hardware fiches
    (GIGABYTE, Raspberry Pi), declared in
    `infrastructure_topology.yml`, no provider observes either. `None`
    (the default) renders the page exactly as before this addition —
    every caller that has not been updated to load and pass a topology
    keeps working unchanged.

    **`beszel_readings` is optional too, same day** — typed snapshots
    from `aistack.architecture.beszel_reading.build_beszel_readings`,
    itself built from `BeszelProvider.collect()`'s raw observation. An
    empty tuple (the default) renders no "État en direct" section at
    all, the same "nothing to show, so show nothing" rule the topology
    sub-blocks already follow.

    **`dependency_graph` is optional too, added the same week** — a
    `DependencyGraph` built by
    `aistack.architecture.dependency_graph.build_dependency_graph`
    from the Compose catalog's own `depends_on:` readings. Unlike
    `topology`/`beszel_readings`, this does not add a static section:
    it adds one more entry to the existing view `<select>` (only when
    at least one project carries a real edge), rendered by
    `render_dependency_mermaid` rather than `render_mermaid` — a
    genuinely different diagram, not a filtered slice of the same
    `ArchitectureGraph` every other view draws from. `None` (the
    default) renders the page exactly as before this addition.

    **`cmdb_readings` is optional too, added 2026-09-23**
    (`claude/PLAN-J11-CONSOLE-2026-09-11.md` §11.9.1, first of the
    three gaps named 2026-09-13) — typed snapshots from
    `aistack.architecture.http_probe_reading.build_http_probe_readings`,
    itself built from `HttpProbeProvider.collect()`'s raw observation.
    An empty tuple (the default) renders no "CMDB temps réel" section
    at all, the same "nothing to show, so show nothing" rule
    `beszel_readings` already follows.

    **Viewport meta and favicon, added 2026-09-30**
    (`claude/AUDIT-CONSOLE-ARCHITECTURE-HEALTH-2026-09-29.md`, constats
    1/3) — this page had neither, unlike Time Machine's own screens
    which already carried a viewport tag. `MARK_DATA_URI` now comes
    from `aistack.renderers.assets`, the same vendored mark
    `console.html` already shows, moved up from `console/assets.py` so
    a renderer outside the console package could reuse it without a
    cross-renderer import.
    """

    if not views or views[0].name != FULL_VIEW:
        raise ValueError(
            "render_html expects views[0] to be the FULL_VIEW view, "
            "the order build_all_views(graph) produces"
        )

    vendored_js = load_vendored_mermaid_js()

    if _SCRIPT_TERMINATOR in vendored_js.lower():
        raise ValueError(
            "The vendored mermaid.js bundle contains "
            f"{_SCRIPT_TERMINATOR!r}, which would truncate the "
            "<script> tag it is embedded in — see vendor/PROVENANCE.md"
        )

    t = translator_for(lang)
    declared = languages if languages is not None else default_languages()

    full = views[0]
    category_count = len(full.graph.categories)
    service_count = sum(len(category.services) for category in full.graph.categories)

    definitions = {view.name: render_mermaid(view) for view in views}

    options_list = [
        f'    <option value="{escape_text(view.name)}">'
        f"{escape_text(_view_label(view.name, t))}</option>"
        for view in views
    ]

    if (
        dependency_graph is not None
        and dependency_graph.projects
        and _DEPENDENCY_VIEW_NAME not in definitions
    ):
        definitions[_DEPENDENCY_VIEW_NAME] = render_dependency_mermaid(
            dependency_graph
        )
        options_list.append(
            f'    <option value="{_DEPENDENCY_VIEW_NAME}">'
            f'{escape_text(t("architecture.view_dependencies"))}</option>'
        )

    # `</` inside a JSON string, re-serialized as `<\/`, is a valid
    # JSON escape (parses back to `/`) and can never terminate the
    # `<script type="application/json">` tag it sits in — the same
    # class of hazard as the vendored bundle above, guarded the same
    # way rather than trusted to not occur in a service or project
    # name.
    data_json = json.dumps(definitions, ensure_ascii=False).replace("</", "<\\/")

    options = "\n".join(options_list)

    service_index_html = _render_service_index(full, t)
    topology_html = _render_topology_section(topology, t)
    beszel_html = _render_beszel_section(beszel_readings, t)
    cmdb_html = _render_cmdb_section(cmdb_readings, t)

    return f"""<!doctype html>
<html lang="{t.lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape_text(t("architecture.title"))}</title>
<link rel="icon" href="{MARK_DATA_URI}">
<style>
{_STYLE}
{PAGE_NAV_STYLE}
</style>
</head>
<body>
{render_page_nav(t, declared, t.lang)}
<header>
  <h1>{escape_text(t("architecture.heading"))}</h1>
  <p class="meta">
    {escape_text(t("architecture.meta", categories=category_count, services=service_count))}
  </p>
</header>

<label for="view-select">{escape_text(t("architecture.view_label"))}</label>
<select id="view-select">
{options}
</select>

<div class="legend">
  <span><span class="swatch swatch-confirmed"></span> {escape_text(t("architecture.legend.confirmed"))}</span>
  <span><span class="swatch swatch-declared"></span> {escape_text(t("architecture.legend.declared"))}</span>
  <span><span class="swatch swatch-none"></span> {escape_text(t("architecture.legend.none"))}</span>
</div>

<div id="diagram" data-unknown-view="{escape_text(t("architecture.unknown_view"))}">{escape_text(t("architecture.loading"))}</div>

{service_index_html}

{topology_html}

{beszel_html}

{cmdb_html}

<script id="views-data" type="application/json">{data_json}</script>
<script>
{vendored_js}
</script>
<script>
{_BOOTSTRAP_JS}
</script>
</body>
</html>
"""


def _view_label(name: str, t: Translator) -> str:
    return t("architecture.view_all") if name == FULL_VIEW else name


def _render_service_index(full: ArchitectureView, t: Translator) -> str:
    """
    Icône + nom + lien + description, une fois par service, groupé par
    catégorie — ajouté 2026-09-12 (`claude/PLAN-J11-CONSOLE-2026-09-11.md`
    §10).

    **Toujours la vue complète, indépendamment du `<select>`.** Le
    graphe Mermaid change de vue au clic ; cette liste ne le suit pas
    — elle énumère `full.graph.categories` une seule fois, pas
    `views[current]`, pour la même raison que `render_html` exige déjà
    `views[0]` comme la vue complète : toutes les catégories n'existent
    ensemble que là.

    **Pas dans le graphe Mermaid lui-même.** Un nœud Mermaid ne peut
    pas porter une image raster arbitraire sans convertir chaque icône
    en pack Iconify — un chantier à part, jugé disproportionné pour ce
    gain (décidé avec le owner). Le clic + info-bulle sur chaque nœud
    (`click <id> href ... _blank`, `mermaid.py`) reste la façon dont
    `href`/`description` s'expriment dans le graphe ; cette liste est
    la façon dont l'icône s'exprime, à côté.
    """

    sections: list[str] = []

    for category in full.graph.categories:
        items: list[str] = []

        for service in category.services:
            icon_data_uri = load_icon_data_uri(service.icon)
            icon_html = (
                f'<img class="service-icon" src="{icon_data_uri}" alt="" />'
                if icon_data_uri
                else '<span class="service-icon service-icon-none"></span>'
            )

            name = escape_text(service.name)
            name_html = (
                f'<a href="{escape_text(service.href)}" target="_blank" '
                f'rel="noopener">{name}</a>'
                if service.href
                else f"<span>{name}</span>"
            )

            description_html = (
                f'<p class="service-description">{escape_text(service.description)}</p>'
                if service.description
                else ""
            )

            items.append(
                "      <li>"
                f"{icon_html}"
                '<span class="service-entry">'
                f"{name_html}"
                f"{description_html}"
                "</span>"
                "</li>"
            )

        sections.append(
            '  <div class="service-category">\n'
            f"    <h3>{escape_text(category.name)}</h3>\n"
            '    <ul class="service-list">\n'
            + "\n".join(items)
            + "\n    </ul>\n"
            "  </div>"
        )

    return (
        '<section class="service-index">\n'
        f'  <h2>{escape_text(t("architecture.services_heading"))}</h2>\n'
        + "\n".join(sections)
        + "\n</section>"
    )


def _render_topology_section(
    topology: InfrastructureTopologyDefinition | None,
    t: Translator,
) -> str:
    """
    Topologie réseau externe + fiches matérielles — ajouté 2026-09-12
    (`claude/PLAN-J11-CONSOLE-2026-09-11.md` §10, deuxième moitié du
    même gap que `_render_service_index`).

    **`None` or an entirely empty topology renders nothing at all** —
    an empty string, not an empty `<section>` — so a page built
    without a topology file (every caller before this one was updated)
    looks exactly as it did before. Each of the two blocks
    (`external_nodes`, `hardware`) is independently optional within a
    non-empty topology too: a topology declaring only one of the two
    still renders just that block.
    """

    if topology is None:
        return ""

    blocks: list[str] = []

    if topology.external_nodes:
        blocks.append(_render_external_nodes_block(topology.external_nodes, t))

    if topology.hardware:
        blocks.append(_render_hardware_block(topology.hardware, t))

    if not blocks:
        return ""

    return (
        '<section class="topology-index">\n'
        f'  <h2>{escape_text(t("architecture.topology.heading"))}</h2>\n'
        + "\n".join(blocks)
        + "\n</section>"
    )


def _render_external_nodes_block(nodes: tuple, t: Translator) -> str:
    items = []

    for node in nodes:
        description_html = (
            f'<p class="topology-description">{escape_text(node.description)}</p>'
            if node.description
            else ""
        )
        items.append(
            "      <li>"
            f'<span class="topology-name">{escape_text(node.name)}</span>'
            f'<span class="topology-role">{escape_text(node.role)}</span>'
            f"{description_html}"
            "</li>"
        )

    return (
        '  <div class="topology-block">\n'
        f'    <h3>{escape_text(t("architecture.topology.external"))}</h3>\n'
        '    <ul class="topology-list">\n'
        + "\n".join(items)
        + "\n    </ul>\n"
        "  </div>"
    )


def _render_hardware_block(profiles: tuple, t: Translator) -> str:
    cards = []

    for profile in profiles:
        gpu_row = (
            f'<dt>{escape_text(t("architecture.spec.gpu"))}</dt><dd>{escape_text(profile.gpu)}</dd>'
            if profile.gpu
            else ""
        )
        cards.append(
            '      <li class="hardware-card">\n'
            f"        <h4>{escape_text(profile.name)}</h4>\n"
            f'        <p class="hardware-model">{escape_text(profile.model)}</p>\n'
            '        <dl class="hardware-specs">\n'
            f'          <dt>{escape_text(t("architecture.spec.cpu"))}</dt><dd>{escape_text(profile.cpu)}</dd>\n'
            f'          <dt>{escape_text(t("architecture.spec.ram"))}</dt><dd>{escape_text(profile.ram)}</dd>\n'
            f"          {gpu_row}\n"
            f'          <dt>{escape_text(t("architecture.spec.storage"))}</dt><dd>{escape_text(profile.storage)}</dd>\n'
            f'          <dt>{escape_text(t("architecture.spec.os"))}</dt><dd>{escape_text(profile.os_name)}</dd>\n'
            f'          <dt>{escape_text(t("architecture.spec.role"))}</dt><dd>{escape_text(profile.role)}</dd>\n'
            "        </dl>\n"
            "      </li>"
        )

    return (
        '  <div class="topology-block">\n'
        f'    <h3>{escape_text(t("architecture.topology.hardware"))}</h3>\n'
        '    <ul class="hardware-list">\n'
        + "\n".join(cards)
        + "\n    </ul>\n"
        "  </div>"
    )


def _render_beszel_section(
    readings: tuple[BeszelSystemReading, ...],
    t: Translator,
) -> str:
    """
    « État en direct » — un instantané par système Beszel, pris au
    moment de la génération, ajouté 2026-09-12
    (`claude/PLAN-J11-CONSOLE-2026-09-11.md` §10, dernier tiret).

    An empty `readings` renders nothing at all — the same "nothing to
    show" rule `_render_topology_section` already follows, so a page
    generated without Beszel configured (or while its provider is
    unreachable) looks exactly as it did before this section existed.
    """

    if not readings:
        return ""

    cards = "\n".join(_render_beszel_card(reading, t) for reading in readings)

    return (
        '<section class="beszel-index">\n'
        f'  <h2>{escape_text(t("architecture.beszel.heading"))}</h2>\n'
        '  <ul class="beszel-list">\n'
        f"{cards}\n"
        "  </ul>\n"
        "</section>"
    )


def _render_beszel_card(reading: BeszelSystemReading, t: Translator) -> str:
    status_class = "beszel-status-up" if reading.status == "up" else "beszel-status-other"

    def label(key: str) -> str:
        return escape_text(t(key))

    rows = [
        (
            f'        <dt>{label("architecture.beszel.status")}</dt>'
            f'<dd><span class="beszel-status {status_class}">'
            f"{escape_text(reading.status or '?')}</span></dd>"
        )
    ]

    if reading.cpu_pct is not None:
        rows.append(
            f'        <dt>{label("architecture.beszel.cpu")}</dt><dd>{reading.cpu_pct:.1f} %</dd>'
        )

    if reading.mem_pct is not None:
        rows.append(
            f'        <dt>{label("architecture.beszel.memory")}</dt><dd>{reading.mem_pct:.1f} %</dd>'
        )

    if reading.disk_pct is not None:
        rows.append(
            f'        <dt>{label("architecture.beszel.disk")}</dt><dd>{reading.disk_pct:.1f} %</dd>'
        )

    if reading.temp_c is not None:
        rows.append(
            f'        <dt>{label("architecture.beszel.temperature")}</dt>'
            f"<dd>{reading.temp_c:.1f} °C</dd>"
        )

    if reading.load_avg is not None:
        one, five, fifteen = reading.load_avg
        rows.append(
            f'        <dt>{label("architecture.beszel.load")}</dt>'
            f"<dd>{one:.2f} / {five:.2f} / {fifteen:.2f}</dd>"
        )

    if reading.uptime_seconds is not None:
        rows.append(
            f'        <dt>{label("architecture.beszel.uptime")}</dt>'
            f"<dd>{escape_text(_format_uptime(reading.uptime_seconds, t))}</dd>"
        )

    return (
        '      <li class="beszel-card">\n'
        f"        <h4>{escape_text(reading.name)}</h4>\n"
        + (
            f'        <p class="beszel-host">{escape_text(reading.host)}</p>\n'
            if reading.host
            else ""
        )
        + '        <dl class="beszel-specs">\n'
        + "\n".join(rows)
        + "\n        </dl>\n"
        "      </li>"
    )


def _format_uptime(seconds: int, t: Translator) -> str:
    """
    Whole days and whole hours, labelled in the page's own language
    (`j`/`h` in French, `d`/`h` in English, ADR-0010) — the same
    register as every other label on this page. Under a day: hours
    and minutes instead, so a system rebooted an hour ago does not
    read as "0 j".
    """

    if seconds < 0:
        return t("architecture.uptime.zero")

    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)

    if days > 0:
        return t("architecture.uptime.days_hours", days=days, hours=hours)

    if hours > 0:
        return t("architecture.uptime.hours_minutes", hours=hours, minutes=minutes)

    return t("architecture.uptime.minutes", minutes=minutes)


def _render_cmdb_section(
    readings: tuple[HttpProbeReading, ...],
    t: Translator,
) -> str:
    """
    « CMDB temps réel » — un instantané par cible HTTP, pris au moment
    de la génération, ajouté 2026-09-23
    (`claude/PLAN-J11-CONSOLE-2026-09-11.md` §11.9.1, premier des trois
    écarts nommés le 2026-09-13).

    An empty `readings` renders nothing at all — the same "nothing to
    show" rule `_render_beszel_section` already follows, so a page
    generated without any target configured looks exactly as it did
    before this section existed.
    """

    if not readings:
        return ""

    cards = "\n".join(_render_cmdb_card(reading, t) for reading in readings)

    return (
        '<section class="cmdb-index">\n'
        f'  <h2>{escape_text(t("architecture.cmdb.heading"))}</h2>\n'
        '  <ul class="cmdb-list">\n'
        f"{cards}\n"
        "  </ul>\n"
        "</section>"
    )


def _render_cmdb_card(reading: HttpProbeReading, t: Translator) -> str:
    status_class, status_label = _cmdb_status(reading, t)

    return (
        '      <li class="cmdb-card">\n'
        f"        <h4>{escape_text(reading.name)}</h4>\n"
        f'        <p class="cmdb-url">{escape_text(reading.url)}</p>\n'
        f'        <span class="cmdb-status {status_class}">'
        f"{escape_text(status_label)}</span>\n"
        "      </li>"
    )


def _cmdb_status(reading: HttpProbeReading, t: Translator) -> tuple[str, str]:
    """
    Three states, not two — unlike Beszel's own up/other split. A
    successful response (2xx/3xx) is `ok`; an HTTP error status the
    server still answered with (4xx/5xx) is `error`, distinct from
    `unreachable` (no answer came back at all) — the same distinction
    `HttpProbeProvider._probe` already makes between an
    `urllib.error.HTTPError` (reachable, real status) and every other
    failure (not reachable, no status).
    """

    if not reading.reachable:
        return "cmdb-status-unreachable", t("architecture.cmdb.unreachable")

    if reading.status_code is None:
        return "cmdb-status-error", "?"

    if 200 <= reading.status_code < 400:
        return "cmdb-status-ok", str(reading.status_code)

    return "cmdb-status-error", str(reading.status_code)


# Same charte graphique retouch as `aistack.renderers.console.html`
# (2026-09-26, see that module's own comment for the full rationale
# and where each value comes from) — the palette, and which classes
# stay untouched (the `swatch`/`*-status-*` families keep their
# green/amber/red meaning, only lightly retinted), are identical
# across all three static pages by design, not by shared code — each
# renderer keeps its own literal `_STYLE`.
#
# Width, same reasoning and same value as that module's own comment
# (ADR-0011 §26, 2026-09-29): `min(96vw, 1600px)`. This page's own
# 1100px predated that decision and carried no stated rationale of its
# own for being wider than the other two static pages — converged to
# the same rule as all of them, not kept as a bespoke exception.
_STYLE = """\
:root { color-scheme: light; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
    Helvetica, Arial, sans-serif;
  max-width: min(96vw, 1600px); margin: 2rem auto;
  color: #1f2933; background: #f7f9fc; padding: 0 1rem;
}
h1, h2, h3, h4 {
  font-family: Georgia, "Times New Roman", Times, serif;
  color: #16335c;
}
header { margin-bottom: 1.2rem; }
.meta { color: #5b6b7d; font-size: .85rem; }
select { padding: .4rem .6rem; font-size: 1rem; margin: .3rem 0 1rem; }
#diagram {
  border: 1px solid #dde4ed; border-radius: 8px; padding: 1rem;
  background: #fafafa; overflow: auto;
}
/*
  Added 2026-09-30 (`claude/AUDIT-CONSOLE-ARCHITECTURE-HEALTH-2026-09-
  29.md`, constat 2) — measured, not guessed: rendering this page at
  375px showed every other section reflowing correctly (the existing
  `auto-fit`/`auto-fill` grids already stack to one column on their
  own), but Mermaid renders its SVG with `width="100%"` and an inline
  `max-width`, so it shrinks in step with `#diagram`'s own width —
  proportionally, meaning its label text shrinks too, down to
  illegible on a phone. A minimum width on the SVG itself stops that:
  `#diagram`'s own `overflow: auto` above then scrolls the box
  horizontally instead, keeping every label at a legible, constant
  size regardless of viewport width.
*/
#diagram svg { min-width: 600px; }
.render-error { color: #9c2b2b; white-space: pre-wrap; font-family: monospace; }
.legend {
  display: flex; gap: 1.2rem; flex-wrap: wrap; margin: .6rem 0 1.2rem;
  font-size: .82rem; color: #5b6b7d;
}
.legend span { display: inline-flex; align-items: center; gap: .4rem; }
.swatch {
  width: .9rem; height: .9rem; border-radius: 3px; display: inline-block;
  border: 1px solid;
}
.swatch-confirmed { background: #e4f3ea; border-color: #1f6d43; }
.swatch-declared { background: #faf1d8; border-color: #8a6100; }
.swatch-none { background: #eef0f3; border-color: #5b6b7d; }
.service-index {
  margin-top: 1.8rem; padding-top: 1.2rem; border-top: 1px solid #dde4ed;
}
.service-index h2 { font-size: 1.1rem; margin: 0 0 1rem; }
.service-category { margin-bottom: 1.6rem; }
.service-category:last-child { margin-bottom: 0; }
.service-category h3 {
  font-size: .8rem; font-weight: 700; letter-spacing: .02em;
  text-transform: uppercase; color: #5b6b7d; margin: 0 0 .6rem;
  border-bottom: 1px solid #dde4ed; padding-bottom: .35rem;
}
.service-list {
  list-style: none; margin: 0; padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(15.5rem, 1fr));
  gap: .7rem;
}
.service-list li {
  display: grid; grid-template-columns: 28px 1fr; align-items: center;
  gap: .6rem;
  border: 1px solid #dde4ed; border-radius: 8px; padding: .6rem .8rem;
  background: #fff;
}
.service-icon {
  width: 28px; height: 28px; object-fit: contain; justify-self: center;
}
.service-icon-none {
  width: 28px; height: 28px; border-radius: 6px; background: #eef0f3;
}
.service-entry {
  display: flex; flex-direction: column; gap: .15rem; min-width: 0;
}
.service-entry a, .service-entry span {
  font-weight: 600; line-height: 1.25;
}
.service-entry a { color: #16335c; text-decoration: none; }
.service-entry a:hover { text-decoration: underline; }
.service-description {
  margin: .1rem 0 0; color: #5b6b7d; font-size: .8rem; line-height: 1.35;
}
.topology-index {
  margin-top: 1.8rem; padding-top: 1.2rem; border-top: 1px solid #dde4ed;
}
.topology-index h2 { font-size: 1.1rem; margin: 0 0 1rem; }
.topology-block { margin-bottom: 1.6rem; }
.topology-block:last-child { margin-bottom: 0; }
.topology-block h3 {
  font-size: .8rem; font-weight: 700; letter-spacing: .02em;
  text-transform: uppercase; color: #5b6b7d; margin: 0 0 .6rem;
  border-bottom: 1px solid #dde4ed; padding-bottom: .35rem;
}
.topology-list {
  list-style: none; margin: 0; padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(15.5rem, 1fr));
  gap: .7rem;
}
.topology-list li {
  display: flex; flex-direction: column; gap: .2rem;
  border: 1px solid #dde4ed; border-radius: 8px; padding: .6rem .8rem;
  background: #fff;
}
.topology-name { font-weight: 700; }
.topology-role { color: #5b6b7d; font-size: .85rem; }
.topology-description {
  margin: .2rem 0 0; color: #5b6b7d; font-size: .8rem; line-height: 1.35;
}
.hardware-list {
  list-style: none; margin: 0; padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(18rem, 1fr));
  gap: .8rem;
}
.hardware-card {
  border: 1px solid #dde4ed; border-radius: 8px; padding: .8rem 1rem;
  background: #fff;
}
.hardware-card h4 { margin: 0 0 .2rem; font-size: 1rem; }
.hardware-model { margin: 0 0 .6rem; color: #5b6b7d; font-size: .82rem; }
.hardware-specs {
  margin: 0; display: grid; grid-template-columns: auto 1fr;
  gap: .25rem .6rem; font-size: .82rem;
}
.hardware-specs dt { color: #5b6b7d; font-weight: 600; }
.hardware-specs dd { margin: 0; }
.beszel-index {
  margin-top: 1.8rem; padding-top: 1.2rem; border-top: 1px solid #dde4ed;
}
.beszel-index h2 { font-size: 1.1rem; margin: 0 0 1rem; }
.beszel-list {
  list-style: none; margin: 0; padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(16rem, 1fr));
  gap: .8rem;
}
.beszel-card {
  border: 1px solid #dde4ed; border-radius: 8px; padding: .8rem 1rem;
  background: #fff;
}
.beszel-card h4 { margin: 0 0 .2rem; font-size: 1rem; }
.beszel-host { margin: 0 0 .6rem; color: #5b6b7d; font-size: .82rem; }
.beszel-specs {
  margin: 0; display: grid; grid-template-columns: auto 1fr;
  gap: .25rem .6rem; font-size: .82rem;
}
.beszel-specs dt { color: #5b6b7d; font-weight: 600; }
.beszel-specs dd { margin: 0; }
.beszel-status {
  display: inline-block; padding: .05rem .5rem; border-radius: 999px;
  font-size: .78rem; font-weight: 600; border: 1px solid;
}
.beszel-status-up { background: #e4f3ea; border-color: #1f6d43; color: #1f6d43; }
.beszel-status-other { background: #faf1d8; border-color: #8a6100; color: #8a6100; }
.cmdb-index {
  margin-top: 1.8rem; padding-top: 1.2rem; border-top: 1px solid #dde4ed;
}
.cmdb-index h2 { font-size: 1.1rem; margin: 0 0 1rem; }
.cmdb-list {
  list-style: none; margin: 0; padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(15.5rem, 1fr));
  gap: .7rem;
}
.cmdb-card {
  display: flex; flex-direction: column; gap: .3rem;
  border: 1px solid #dde4ed; border-radius: 8px; padding: .6rem .8rem;
  background: #fff;
}
.cmdb-card h4 { margin: 0; font-size: .95rem; }
.cmdb-url { margin: 0; color: #5b6b7d; font-size: .78rem; word-break: break-all; }
.cmdb-status {
  display: inline-block; align-self: flex-start; padding: .05rem .5rem;
  border-radius: 999px; font-size: .78rem; font-weight: 600; border: 1px solid;
}
.cmdb-status-ok { background: #e4f3ea; border-color: #1f6d43; color: #1f6d43; }
.cmdb-status-error { background: #faf1d8; border-color: #8a6100; color: #8a6100; }
.cmdb-status-unreachable { background: #f9e3e1; border-color: #9c2b2b; color: #9c2b2b; }\
"""

_BOOTSTRAP_JS = """\
(function () {
  var data = JSON.parse(document.getElementById('views-data').textContent);
  var container = document.getElementById('diagram');
  var select = document.getElementById('view-select');
  var counter = 0;

  mermaid.initialize({ startOnLoad: false });

  function draw(name) {
    var definition = data[name];

    if (definition === undefined) {
      var unknown = document.createElement('p');
      unknown.className = 'render-error';
      unknown.textContent = container.dataset.unknownView + ' ' + name;
      container.replaceChildren(unknown);
      return;
    }

    var id = 'architecture-graph-' + (counter += 1);

    mermaid.render(id, definition).then(function (result) {
      container.innerHTML = result.svg;
    }).catch(function (error) {
      var message = error && error.message ? error.message : String(error);
      container.innerHTML = '<p class="render-error">' + message + '</p>';
    });
  }

  select.addEventListener('change', function () {
    draw(select.value);
  });

  draw(select.value);
})();\
"""
