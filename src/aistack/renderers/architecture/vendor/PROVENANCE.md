# `mermaid.min.js` — provenance

Vendored 2026-09-10, for `claude/PLAN-J2-ARCHITECTURE-HTML-2026-09-10.md`
step 5. Decided with the owner: `architecture.html` renders with no
network access at all — vendored inline, not a `<script src="https://
cdn...">` tag — so the file is the same artifact tomorrow as today,
regardless of what a CDN is serving or whether the viewing machine has
a route to it.

## What this file is

- **Source**: `mermaid@11.17.2` from the public npm registry
  (`npm install mermaid@11`).
- **Built from**: that package's own `dist/mermaid.js` — the one file
  under `dist/` that sets `globalThis.mermaid` directly and carries
  every diagram type inlined (no dynamic `import()` of sibling chunk
  files at runtime, unlike `dist/mermaid.esm.mjs` and the `chunks/`
  directory beside it). A page that inlines only one `<script>` tag
  cannot also serve chunk files a dynamic import would otherwise fetch
  by relative path, so this is the only one of mermaid's own dist
  artifacts that fits a single self-contained file.
- **Minified with**: `esbuild --minify` (`npx esbuild dist/mermaid.js
  --minify --outfile=mermaid.min.js`), 8.25 MB → 3.5 MB. Not mermaid's
  own build step — the package ships `dist/mermaid.js` unminified;
  this repository minifies it once, itself, before vendoring it.

## Upgrading

There is no automated step for this — bump the version by hand:

1. `npm install mermaid@<new version>` somewhere scratch, outside this
   repository.
2. Minify `node_modules/mermaid/dist/mermaid.js` the same way, and
   replace this directory's `mermaid.min.js` with the result.
3. Update the version number in this file.
4. Run the full suite. `tests/unit/renderers/architecture/test_html.py`
   guards the one property a new build could break silently — that
   the embedded bundle never contains the literal text `</script`,
   which would truncate the `<script>` tag `render_html` embeds it in
   (checked empirically against 11.17.2: absent).
