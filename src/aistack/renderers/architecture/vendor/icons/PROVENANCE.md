# Service icons — provenance

Vendored 2026-09-12, for `claude/PLAN-J11-CONSOLE-2026-09-11.md` §10 (richness
gap against the pre-AIStack `architecture.html`). Same reasoning as
`vendor/PROVENANCE.md` one directory up: `architecture.html` renders with no
network access at all, so an icon is a file in this repository, not a
`<img src="https://...">` tag pointed at a CDN.

## Where each icon comes from

**39 PNGs — `walkxcode/dashboard-icons`** (the same open icon pack the
pre-AIStack Homepage dashboard read `homepage/services.yaml`'s own `icon:`
field against — `main` branch, fetched 2026-09-12):

```
https://raw.githubusercontent.com/walkxcode/dashboard-icons/main/png/<slug>.png
```

Fetched at native resolution, then downscaled to 48×48 and stripped of
metadata with ImageMagick (`convert <slug>.png -resize 48x48 -strip
<slug>.png`) — full resolution ran 1.4 MB across 39 files for icons this
page only ever displays at a few dozen pixels; downscaled, the same 39
files total 176 KB. Same discipline `renderers/console/assets.py` already
applies to the console's own two PNGs.

`<slug>` is the source `service_categorization.yml`'s own `icon:` value
with the `.png` extension removed — `nginx-proxy-manager`, `portainer`,
`pi-hole`, `nextcloud`, `vaultwarden`, `vikunja`, `stirling-pdf`,
`filebrowser`, `syncthing`, `uptime-kuma`, `scrutiny`, `gotify`,
`librespeed`, `frigate`, `home-assistant`, `immich`, `jellyfin`, `booklore`,
`komga`, `paperless-ngx`, `bookstack`, `wordpress`, `actual-budget`,
`firefly`, `romm`, `overseerr`, `prowlarr`, `radarr`, `sonarr`, `lidarr`,
`readarr`, `mylar`, `bazarr`, `qbittorrent`, `autobrr`, `vscode`, `gitea`,
`cyberchef`, `it-tools`.

**6 SVGs — Material Design Icons, `Templarian/MaterialDesign`** (`master`
branch, fetched 2026-09-12), for services the source declared with an
`mdi-*` icon rather than a dashboard-icons PNG:

```
https://raw.githubusercontent.com/Templarian/MaterialDesign/master/svg/<name>.svg
```

- `router-wireless` — FreeboxOS, Freebox Dashboard (source: `mdi-router-wireless`)
- `monitor-dashboard` — Beszel (source: `mdi-monitor-dashboard`)
- `sitemap` — Architecture Homelab (source: `mdi-sitemap`)
- `download-network` — Mularr (source: `mdi-download-network`)
- `music` — Music Sync (source: `mdi-music`)
- `book-open-page-variant` — Legal to Read. The source declared `icon:
  books`, which is not a valid dashboard-icons slug (`404`, checked
  2026-09-12) and carries no `mdi-`/`fa-` prefix either — it does not
  resolve to anything in either icon set. Owner's call, asked rather than
  guessed: use this Material Design Icons generic book icon instead of the
  source's own dead reference.

**1 SVG — Font Awesome Free 6, `FortAwesome/Font-Awesome`** (`6.x` branch,
fetched 2026-09-12), for the one service the source declared with an
`fa-*` icon:

```
https://raw.githubusercontent.com/FortAwesome/Font-Awesome/6.x/svgs/solid/user-tie.svg
```

- `user-tie` — Indy (source: `fa-user-tie`). Free/solid style; License —
  Icons: CC BY 4.0, Fonts: SIL OFL 1.1, Code: MIT (attribution carried in
  the vendored file's own header comment, untouched).

SVGs are vendored as fetched — small vector files, nothing to downscale.

## What is not vendored

`server`, from the same source file, does not travel here either — same
reasoning `service_categorization.yml`'s own header already gives for
excluding it: AIStack has no provider for which host runs a service.

## Loaded by

`aistack/renderers/architecture/icons.py` — `load_icon_data_uri(key)`,
read from disk beside that module the same
`Path(__file__).resolve()`-relative way `load_vendored_mermaid_js` reads
its own directory up.

## Upgrading

There is no automated step. Re-fetch the specific file from its source
above, re-run the same ImageMagick resize for a PNG, replace it in this
directory, and run the full suite — nothing here is generated, so nothing
regenerates it.
