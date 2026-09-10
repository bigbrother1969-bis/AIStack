from __future__ import annotations

import json
from pathlib import Path

from aistack.architecture.views import FULL_VIEW, ArchitectureView
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
.swatch-none { background: #f0f0f0; border-color: #666; }\
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
