from __future__ import annotations

import json
from pathlib import Path

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


def render_html(views: tuple[ArchitectureView, ...]) -> str:
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
}\
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
