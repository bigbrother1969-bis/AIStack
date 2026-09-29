"""
The time ribbon's second slice — v2 (`ADR-0011` § 26, 1.5.2 cadrage,
2026-09-29). `ADR-0011` § 24 named two real gaps in the v1 ribbon
rather than leaving them to discover: it was "a full, filterable,
chronological list" with no real time axis, and it had no "curseur
d'instant, pas-à-pas" at all. This module is the first of those two
closed — a real horizontal time axis, one lane per stream, instead of
a flat `<ul>`.

**The owner's own cadrage, 2026-09-29, before this module existed**:
SVG + inline vanilla JS, no vendored library and no CDN — the same
self-contained-per-page discipline every Time Machine screen already
holds (`_style.html`'s own docstring), extended here rather than
reaching for a second JS dependency alongside the one `mermaid.min.js`
already vendors (`aistack.renderers.architecture.html`). And the
cursor drives real navigation — click or drag selects the nearest
instant and opens its `/node` card — rather than a decorative control
with nothing behind it: maquette 3's own reconstitution
("reconstituer en trois clics") has no backend at all yet, and
`ARC-P-006` forbids building toward a screen that does not exist.
Dragging the cursor previews a position; releasing it (or a plain
click) is what navigates — never on every `mousemove`, which would
spam the browser with navigations mid-drag.

**Hover uses SVG's own native `<title>` element, not custom JS.** A
`<title>` inside an SVG `<a>`/`<text>` is a real, correctly-positioned
browser tooltip for free, in every browser, on hover or on a
screen-reader's own accessible-name computation — safer than
hand-rolled JS positioning this session cannot pixel-test across
browsers, and it already satisfies the `dataviz` skill's own hover
layer requirement without inventing one.

**Real production data (2026-09-29, the owner's own screenshot of
`/ribbon` in use) found a second real gap this module did not yet
handle: clustering.** Roughly twenty real streams exist today, not
the five to six this module was designed against, and several close
instants on the same lane rendered as one illegible, overlapping
smear (`docker-events` in particular). A fresh cadrage (`AskUserQuestion`)
settled two decisions before any code:

1. **Streams group by category, foldable** — the owner's own choice,
   over leaving every stream flat or hiding the least-active ones by
   default. The grouping this module and its caller use is not
   invented: the only two kinds of stream this graph's own code
   distinguishes today are the four 1.5 Docker collectors, each its
   own dedicated projector module declaring its own `STEM` constant
   (`docker_events`/`docker_diff`/`docker_digest`/`docker_packages`),
   and everything else — every other stream shares the exact same
   generic `project_observation_history` walk and the exact same IRI
   scheme (`aistack.timemachine.iri.stream_iri`), so there is no real,
   already-existing distinction to subdivide it further without
   inventing a taxonomy nothing in this graph states
   (`ARC-P-006`). `timemachine_ui.app`'s `ribbon_view` builds one
   `RibbonSvg` per category by calling `render_ribbon_svg` twice —
   this module itself stays generic, with no notion of "Docker" or
   "observation" anywhere in it, the same reasoning `iri.py`'s own
   docstring already states for staying prefix-agnostic.
2. **Marks too close together to tell apart merge into one counted
   cluster** — the owner's own choice, over a zoomable axis (real
   interaction state to build and test) or a non-linear axis
   (compressing real time proportions would contradict "rien de
   deviné, tout mesuré"). `_cluster_lane` below groups consecutive
   same-lane marks whose pixel distance falls under
   `_CLUSTER_MIN_GAP_PX` and renders them as one glyph with a count
   suffix (`"●3"`), never dropping data: the merged mark's own
   `<title>` lists every member instant, and the merged mark's own
   `href` still opens a real `/node` card (the earliest member's).
   **Narrower than the option's own "qui se déplie" wording, named
   here rather than left to discover**: this v1 does not unfold a
   cluster back into its individual marks in place — the same
   restraint already applied to the cursor's own real-but-narrower
   scope (never the reconstruction maquette 3 would need). Every
   clustered instant remains fully visible, unclustered, in the flat
   `.band-list` this page already keeps beneath the graphic.

**All the geometry lives here, pure and deterministic** (same
`RibbonMark`/`href`-arrives-pre-built contract
`aistack.renderers.timemachine.provenance_mermaid.ProvenanceNeighbor`
already holds), so it is testable by the governed suite without a
browser (`R5`: "toute la logique dans `src/`, testée ; couches web
minces"). `ribbon_view` in `timemachine_ui/app.py` calls
`render_ribbon_svg` with the same already-built `filtered` entries it
already renders as a flat list — kept, unremoved: the `dataviz`
skill's own non-negotiable, "a table view exists".

**Deliberately still narrower than the validated maquette.** Not
built here, named rather than left to discover: the network tree
shown paired alongside the ribbon (`/tree` stays a separate view —
merging the two is real future design); the event card's own
"panneau Pourquoi" (1.7's own concern, `ADR-0011` § 24 already named
it); the cursor itself only ever opens the nearest instant's existing
`/node` drill-down — it does not reconstruct anything; and a cluster
mark does not unfold in place (above).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from aistack.renderers.text import escape_text

_VIEWBOX_WIDTH = 900
_LEFT_GUTTER = 150
_RIGHT_MARGIN = 20
_TOP_MARGIN = 20
_LANE_HEIGHT = 34
_AXIS_LABEL_HEIGHT = 24
_MARK_FONT_SIZE = 15

# A glyph at `_MARK_FONT_SIZE` is comfortably wider than this on every
# font this heritage's own charte already relies on (system sans-serif
# — `_style.html`'s own `body { font-family: sans-serif; }`) — two
# marks closer together than this on the same lane are the "illegible
# smear" the owner's own screenshot showed for `docker-events`, not a
# real visual gap between two distinguishable marks.
_CLUSTER_MIN_GAP_PX = 14.0


@dataclass(frozen=True)
class RibbonMark:
    """
    One already-decided instant to place on the ribbon — exactly one
    row of `ribbon_view`'s existing `filtered` list, unpacked into the
    fields this renderer draws. `href` and `color`/`shape` arrive
    pre-built (the caller's existing badge assignment and
    `_node_href`), the same "hrefs arrive pre-built" contract
    `ProvenanceNeighbor` already holds — this module draws a picture
    from already-decided data, never a router itself.

    `instant` is the `str` `ribbon_view` already carries — always a
    `datetime.isoformat()` lexical form, because every projector that
    writes `prov:generatedAtTime`/`aistack:occurredAt` agrees on that
    one shape (`docker_events.py`, `docker_diff.py`, `docker_digest.py`,
    `docker_packages.py`, `collection_gaps.py`, `explications.py`,
    `projection/__init__.py`) — `datetime.fromisoformat` is this
    format's own exact inverse, not a looser general parser.
    """

    href: str
    stream: str
    instant: str
    subject: str | None
    is_gap: bool
    is_occurred_at: bool
    color: str
    shape: str


@dataclass(frozen=True)
class RibbonSvg:
    """The rendered picture, plus the one count the template needs to
    decide whether to show it at all — `ribbon_view` already knows
    `bool(entries)`, this exists only so a future caller need not
    recount `marks` itself."""

    markup: str
    mark_count: int


@dataclass(frozen=True)
class _Positioned:
    """One mark, already placed on the time axis — the unit
    `_cluster_lane` groups."""

    x: float
    instant: datetime
    mark: RibbonMark


def _parse(instant: str) -> datetime:
    return datetime.fromisoformat(instant)


def _cluster_lane(positioned: list[_Positioned]) -> list[list[_Positioned]]:
    """
    Group one lane's own marks, already sorted by `x`, into clusters:
    a run of consecutive marks each within `_CLUSTER_MIN_GAP_PX` of the
    previous one joins the same cluster, so three marks 5px apart each
    become one cluster of three even though the first and third are
    28px apart — the same "too close to the one right next to it"
    reading a viewer's own eye would apply, not a fixed window around
    one fixed centre.
    """

    if not positioned:
        return []

    clusters: list[list[_Positioned]] = [[positioned[0]]]
    for item in positioned[1:]:
        if item.x - clusters[-1][-1].x < _CLUSTER_MIN_GAP_PX:
            clusters[-1].append(item)
        else:
            clusters.append([item])
    return clusters


def _render_cluster(cluster: list[_Positioned], y: float) -> tuple[str, str]:
    """
    One cluster's own `<a><text>...` element, plus its own JSON cursor
    point. A single-member cluster renders exactly as § 24's original
    single-mark case; a multi-member cluster keeps the lane's own
    colour/shape (every member shares it — one lane is one stream) and
    appends its own count, never averaging or dropping a member's own
    instant out of the tooltip.
    """

    first = cluster[0].mark
    x = sum(item.x for item in cluster) / len(cluster)
    any_gap = any(item.mark.is_gap for item in cluster)
    css_class = "ribbon-mark ribbon-mark--gap" if any_gap else "ribbon-mark"
    if len(cluster) > 1:
        css_class += " ribbon-mark--cluster"
        glyph = f"{first.shape}{len(cluster)}"
    else:
        glyph = first.shape

    tooltip_lines: list[str] = []
    for item in cluster:
        bits = [item.mark.stream, item.instant.isoformat(timespec="seconds")]
        if item.mark.subject:
            bits.append(item.mark.subject)
        if not item.mark.is_occurred_at:
            bits.append("enregistré")
        if item.mark.is_gap:
            bits.append("trou de collecte")
        tooltip_lines.append(" — ".join(bits))
    tooltip = escape_text("\n".join(tooltip_lines))

    element = (
        f'<a href="{first.href}"><text x="{x:.1f}" y="{y + 5:.1f}" '
        f'text-anchor="middle" class="{css_class}" '
        f'style="fill:{escape_text(first.color)}" '
        f'font-size="{_MARK_FONT_SIZE}">'
        f"<title>{tooltip}</title>{escape_text(glyph)}</text></a>"
    )
    cursor_point = f'{{"x":{x:.2f},"href":"{first.href}"}}'
    return element, cursor_point


def render_ribbon_svg(marks: tuple[RibbonMark, ...], streams: tuple[str, ...]) -> RibbonSvg:
    """
    Render every mark on a real horizontal time axis, one lane per
    stream, in the caller's own given order (`ribbon_view`'s already-
    sorted `all_streams`, or one category's own subset of it) — a
    lane's row never reshuffles when a filter hides another stream,
    the same stable-badge guarantee `ribbon_view`'s own docstring
    already states for colour/shape.

    Deterministic given the same input, the same discipline
    `render_provenance_mermaid` already holds.

    An empty `marks` tuple (every stream filtered out, a real state
    `ribbon_view`'s own all-boxes-unchecked submission already lets
    happen) still renders a real axis line and the lane rows
    themselves — never a crash, and never a fabricated instant.
    """

    lane_y = {
        stream: _TOP_MARGIN + index * _LANE_HEIGHT + _LANE_HEIGHT / 2
        for index, stream in enumerate(streams)
    }
    axis_y = _TOP_MARGIN + len(streams) * _LANE_HEIGHT + 14
    height = axis_y + _AXIS_LABEL_HEIGHT + 6

    parts: list[str] = [
        f'<svg viewBox="0 0 {_VIEWBOX_WIDTH} {height:.0f}" role="img" '
        f'aria-label="Ruban du temps" class="ribbon-svg" '
        f'data-cursor-min-x="{_LEFT_GUTTER}" '
        f'data-cursor-max-x="{_VIEWBOX_WIDTH - _RIGHT_MARGIN}">'
    ]

    for stream, y in lane_y.items():
        parts.append(
            f'<line x1="{_LEFT_GUTTER}" y1="{y:.1f}" '
            f'x2="{_VIEWBOX_WIDTH - _RIGHT_MARGIN}" y2="{y:.1f}" '
            f'class="ribbon-lane-line"></line>'
        )
        parts.append(
            f'<text x="6" y="{y + 4:.1f}" class="ribbon-lane-label">'
            f"{escape_text(stream)}</text>"
        )

    parts.append(
        f'<line x1="{_LEFT_GUTTER}" y1="{axis_y:.1f}" '
        f'x2="{_VIEWBOX_WIDTH - _RIGHT_MARGIN}" y2="{axis_y:.1f}" '
        f'class="ribbon-axis-line"></line>'
    )

    cursor_points: list[str] = []
    if marks:
        instants = [_parse(mark.instant) for mark in marks]
        earliest, latest = min(instants), max(instants)
        span = (latest - earliest).total_seconds()
        plot_left = float(_LEFT_GUTTER)
        plot_right = float(_VIEWBOX_WIDTH - _RIGHT_MARGIN)

        def x_of(instant: datetime) -> float:
            if span <= 0:
                return (plot_left + plot_right) / 2
            fraction = (instant - earliest).total_seconds() / span
            return plot_left + fraction * (plot_right - plot_left)

        for label_instant, anchor in ((earliest, "start"), (latest, "end")):
            parts.append(
                f'<text x="{x_of(label_instant):.1f}" y="{axis_y + 16:.1f}" '
                f'text-anchor="{anchor}" class="ribbon-axis-label">'
                f"{escape_text(label_instant.isoformat(timespec='seconds'))}</text>"
            )

        by_lane: dict[str, list[_Positioned]] = {stream: [] for stream in streams}
        for mark, instant in zip(marks, instants, strict=True):
            by_lane.setdefault(mark.stream, []).append(
                _Positioned(x=x_of(instant), instant=instant, mark=mark)
            )

        first_x: float | None = None
        for stream in streams:
            lane_marks = sorted(by_lane.get(stream, []), key=lambda item: item.x)
            for cluster in _cluster_lane(lane_marks):
                element, cursor_point = _render_cluster(cluster, lane_y[stream])
                parts.append(element)
                cursor_points.append(cursor_point)
                if first_x is None:
                    first_x = cluster[0].x

        if first_x is not None:
            parts.append(
                f'<line x1="{first_x:.1f}" y1="0" '
                f'x2="{first_x:.1f}" y2="{height:.0f}" '
                'class="ribbon-cursor" style="display:none"></line>'
            )

    parts.append("</svg>")
    if cursor_points:
        parts.append(
            '<script type="application/json" class="ribbon-marks-data">'
            f'[{",".join(cursor_points)}]</script>'
        )

    return RibbonSvg(markup="".join(parts), mark_count=len(marks))
