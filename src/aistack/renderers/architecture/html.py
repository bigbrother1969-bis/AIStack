from __future__ import annotations

import json
from pathlib import Path

from aistack.architecture.beszel_reading import BeszelSystemReading
from aistack.architecture.topology_definition import InfrastructureTopologyDefinition
from aistack.architecture.views import FULL_VIEW, ArchitectureView
from aistack.renderers.architecture.icons import load_icon_data_uri
from aistack.renderers.architecture.mermaid import escape_text, render_mermaid

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

    full = views[0]
    category_count = len(full.graph.categories)
    service_count = sum(len(category.services) for category in full.graph.categories)

    definitions = {view.name: render_mermaid(view) for view in views}
    # `</` inside a JSON string, re-serialized as `<\/`, is a valid
    # JSON escape (parses back to `/`) and can never terminate the
    # `<script type="application/json">` tag it sits in — the same
    # class of hazard as the vendored bundle above, guarded the same
    # way rather than trusted to not occur in a service or project
    # name.
    data_json = json.dumps(definitions, ensure_ascii=False).replace("</", "<\\/")

    options = "\n".join(
        f'    <option value="{escape_text(view.name)}">'
        f"{escape_text(_view_label(view.name))}</option>"
        for view in views
    )

    service_index_html = _render_service_index(full)
    topology_html = _render_topology_section(topology)
    beszel_html = _render_beszel_section(beszel_readings)

    return f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>AIStack — Architecture</title>
<style>
{_STYLE}
</style>
</head>
<body>
<header>
  <h1>Architecture — AIStack</h1>
  <p class="meta">
    {category_count} catégorie(s), {service_count} service(s) déclaré(s)
  </p>
</header>

<label for="view-select">Vue</label>
<select id="view-select">
{options}
</select>

<div class="legend">
  <span><span class="swatch swatch-confirmed"></span> observé (Docker ou Compose)</span>
  <span><span class="swatch swatch-declared"></span> déclaré, non observé</span>
  <span><span class="swatch swatch-none"></span> sans conteneur déclaré</span>
</div>

<div id="diagram">Chargement…</div>

{service_index_html}

{topology_html}

{beszel_html}

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


def _view_label(name: str) -> str:
    return "Toutes les catégories" if name == FULL_VIEW else name


def _render_service_index(full: ArchitectureView) -> str:
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
        "  <h2>Services déclarés</h2>\n"
        + "\n".join(sections)
        + "\n</section>"
    )


def _render_topology_section(
    topology: InfrastructureTopologyDefinition | None,
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
        blocks.append(_render_external_nodes_block(topology.external_nodes))

    if topology.hardware:
        blocks.append(_render_hardware_block(topology.hardware))

    if not blocks:
        return ""

    return (
        '<section class="topology-index">\n'
        "  <h2>Topologie &amp; matériel</h2>\n"
        + "\n".join(blocks)
        + "\n</section>"
    )


def _render_external_nodes_block(nodes: tuple) -> str:
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
        "    <h3>Topologie réseau externe</h3>\n"
        '    <ul class="topology-list">\n'
        + "\n".join(items)
        + "\n    </ul>\n"
        "  </div>"
    )


def _render_hardware_block(profiles: tuple) -> str:
    cards = []

    for profile in profiles:
        gpu_row = (
            f"<dt>GPU</dt><dd>{escape_text(profile.gpu)}</dd>"
            if profile.gpu
            else ""
        )
        cards.append(
            '      <li class="hardware-card">\n'
            f"        <h4>{escape_text(profile.name)}</h4>\n"
            f'        <p class="hardware-model">{escape_text(profile.model)}</p>\n'
            '        <dl class="hardware-specs">\n'
            f"          <dt>CPU</dt><dd>{escape_text(profile.cpu)}</dd>\n"
            f"          <dt>RAM</dt><dd>{escape_text(profile.ram)}</dd>\n"
            f"          {gpu_row}\n"
            f"          <dt>Stockage</dt><dd>{escape_text(profile.storage)}</dd>\n"
            f"          <dt>OS</dt><dd>{escape_text(profile.os_name)}</dd>\n"
            f"          <dt>Rôle</dt><dd>{escape_text(profile.role)}</dd>\n"
            "        </dl>\n"
            "      </li>"
        )

    return (
        '  <div class="topology-block">\n'
        "    <h3>Fiches matérielles</h3>\n"
        '    <ul class="hardware-list">\n'
        + "\n".join(cards)
        + "\n    </ul>\n"
        "  </div>"
    )


def _render_beszel_section(
    readings: tuple[BeszelSystemReading, ...],
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

    cards = "\n".join(_render_beszel_card(reading) for reading in readings)

    return (
        '<section class="beszel-index">\n'
        "  <h2>État en direct (Beszel)</h2>\n"
        '  <ul class="beszel-list">\n'
        f"{cards}\n"
        "  </ul>\n"
        "</section>"
    )


def _render_beszel_card(reading: BeszelSystemReading) -> str:
    status_class = "beszel-status-up" if reading.status == "up" else "beszel-status-other"

    rows = [
        (
            '        <dt>Statut</dt>'
            f'<dd><span class="beszel-status {status_class}">'
            f"{escape_text(reading.status or '?')}</span></dd>"
        )
    ]

    if reading.cpu_pct is not None:
        rows.append(f"        <dt>CPU</dt><dd>{reading.cpu_pct:.1f} %</dd>")

    if reading.mem_pct is not None:
        rows.append(f"        <dt>Mémoire</dt><dd>{reading.mem_pct:.1f} %</dd>")

    if reading.disk_pct is not None:
        rows.append(f"        <dt>Disque</dt><dd>{reading.disk_pct:.1f} %</dd>")

    if reading.temp_c is not None:
        rows.append(f"        <dt>Température</dt><dd>{reading.temp_c:.1f} °C</dd>")

    if reading.load_avg is not None:
        one, five, fifteen = reading.load_avg
        rows.append(
            "        <dt>Charge</dt>"
            f"<dd>{one:.2f} / {five:.2f} / {fifteen:.2f}</dd>"
        )

    if reading.uptime_seconds is not None:
        rows.append(
            f"        <dt>Disponibilité</dt><dd>{_format_uptime(reading.uptime_seconds)}</dd>"
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


def _format_uptime(seconds: int) -> str:
    """
    Whole days and whole hours, French-labelled (`j`/`h`) — the same
    register as every other label on this page. Under a day: hours
    and minutes instead, so a system rebooted an hour ago does not
    read as "0 j".
    """

    if seconds < 0:
        return "0 h"

    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)

    if days > 0:
        return f"{days} j {hours} h"

    if hours > 0:
        return f"{hours} h {minutes} min"

    return f"{minutes} min"



_STYLE = """\
:root { color-scheme: light; }
body {
  font-family: sans-serif; max-width: 1100px; margin: 2rem auto;
  color: #1f2933; padding: 0 1rem;
}
header { margin-bottom: 1.2rem; }
.meta { color: #666; font-size: .85rem; }
select { padding: .4rem .6rem; font-size: 1rem; margin: .3rem 0 1rem; }
#diagram {
  border: 1px solid #ddd; border-radius: 8px; padding: 1rem;
  background: #fafafa; overflow: auto;
}
.render-error { color: #b00020; white-space: pre-wrap; font-family: monospace; }
.legend {
  display: flex; gap: 1.2rem; flex-wrap: wrap; margin: .6rem 0 1.2rem;
  font-size: .82rem; color: #444;
}
.legend span { display: inline-flex; align-items: center; gap: .4rem; }
.swatch {
  width: .9rem; height: .9rem; border-radius: 3px; display: inline-block;
  border: 1px solid;
}
.swatch-confirmed { background: #dff6dd; border-color: #116329; }
.swatch-declared { background: #fff1cc; border-color: #7d4e00; }
.swatch-none { background: #f0f0f0; border-color: #666; }
.service-index {
  margin-top: 1.8rem; padding-top: 1.2rem; border-top: 1px solid #e5e5e5;
}
.service-index h2 { font-size: 1.1rem; margin: 0 0 1rem; }
.service-category { margin-bottom: 1.6rem; }
.service-category:last-child { margin-bottom: 0; }
.service-category h3 {
  font-size: .8rem; font-weight: 700; letter-spacing: .02em;
  text-transform: uppercase; color: #666; margin: 0 0 .6rem;
  border-bottom: 1px solid #e5e5e5; padding-bottom: .35rem;
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
  border: 1px solid #e5e5e5; border-radius: 8px; padding: .6rem .8rem;
  background: #fff;
}
.service-icon {
  width: 28px; height: 28px; object-fit: contain; justify-self: center;
}
.service-icon-none {
  width: 28px; height: 28px; border-radius: 6px; background: #f0f0f0;
}
.service-entry {
  display: flex; flex-direction: column; gap: .15rem; min-width: 0;
}
.service-entry a, .service-entry span {
  font-weight: 600; line-height: 1.25;
}
.service-entry a { color: #0b5fff; text-decoration: none; }
.service-entry a:hover { text-decoration: underline; }
.service-description {
  margin: .1rem 0 0; color: #666; font-size: .8rem; line-height: 1.35;
}
.topology-index {
  margin-top: 1.8rem; padding-top: 1.2rem; border-top: 1px solid #e5e5e5;
}
.topology-index h2 { font-size: 1.1rem; margin: 0 0 1rem; }
.topology-block { margin-bottom: 1.6rem; }
.topology-block:last-child { margin-bottom: 0; }
.topology-block h3 {
  font-size: .8rem; font-weight: 700; letter-spacing: .02em;
  text-transform: uppercase; color: #666; margin: 0 0 .6rem;
  border-bottom: 1px solid #e5e5e5; padding-bottom: .35rem;
}
.topology-list {
  list-style: none; margin: 0; padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(15.5rem, 1fr));
  gap: .7rem;
}
.topology-list li {
  display: flex; flex-direction: column; gap: .2rem;
  border: 1px solid #e5e5e5; border-radius: 8px; padding: .6rem .8rem;
  background: #fff;
}
.topology-name { font-weight: 700; }
.topology-role { color: #444; font-size: .85rem; }
.topology-description {
  margin: .2rem 0 0; color: #666; font-size: .8rem; line-height: 1.35;
}
.hardware-list {
  list-style: none; margin: 0; padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(18rem, 1fr));
  gap: .8rem;
}
.hardware-card {
  border: 1px solid #e5e5e5; border-radius: 8px; padding: .8rem 1rem;
  background: #fff;
}
.hardware-card h4 { margin: 0 0 .2rem; font-size: 1rem; }
.hardware-model { margin: 0 0 .6rem; color: #666; font-size: .82rem; }
.hardware-specs {
  margin: 0; display: grid; grid-template-columns: auto 1fr;
  gap: .25rem .6rem; font-size: .82rem;
}
.hardware-specs dt { color: #666; font-weight: 600; }
.hardware-specs dd { margin: 0; }
.beszel-index {
  margin-top: 1.8rem; padding-top: 1.2rem; border-top: 1px solid #e5e5e5;
}
.beszel-index h2 { font-size: 1.1rem; margin: 0 0 1rem; }
.beszel-list {
  list-style: none; margin: 0; padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(16rem, 1fr));
  gap: .8rem;
}
.beszel-card {
  border: 1px solid #e5e5e5; border-radius: 8px; padding: .8rem 1rem;
  background: #fff;
}
.beszel-card h4 { margin: 0 0 .2rem; font-size: 1rem; }
.beszel-host { margin: 0 0 .6rem; color: #666; font-size: .82rem; }
.beszel-specs {
  margin: 0; display: grid; grid-template-columns: auto 1fr;
  gap: .25rem .6rem; font-size: .82rem;
}
.beszel-specs dt { color: #666; font-weight: 600; }
.beszel-specs dd { margin: 0; }
.beszel-status {
  display: inline-block; padding: .05rem .5rem; border-radius: 999px;
  font-size: .78rem; font-weight: 600; border: 1px solid;
}
.beszel-status-up { background: #dff6dd; border-color: #116329; color: #116329; }
.beszel-status-other { background: #fff1cc; border-color: #7d4e00; color: #7d4e00; }\
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
      container.innerHTML = '<p class="render-error">Vue inconnue : ' + name + '</p>';
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
