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
it); and the cursor itself only ever opens the nearest instant's
existing `/node` drill-down — it does not reconstruct anything.
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


def _parse(instant: str) -> datetime:
    return datetime.fromisoformat(instant)


def render_ribbon_svg(marks: tuple[RibbonMark, ...], streams: tuple[str, ...]) -> RibbonSvg:
    """
    Render every mark on a real horizontal time axis, one lane per
    stream, in the caller's own given order (`ribbon_view`'s already-
    sorted `all_streams`) — a lane's row never reshuffles when a
    filter hides another stream, the same stable-badge guarantee
    `ribbon_view`'s own docstring already states for colour/shape.

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

        for mark, instant in zip(marks, instants, strict=True):
            x = x_of(instant)
            y = lane_y[mark.stream]
            css_class = "ribbon-mark ribbon-mark--gap" if mark.is_gap else "ribbon-mark"
            tooltip_bits = [mark.stream, instant.isoformat(timespec="seconds")]
            if mark.subject:
                tooltip_bits.append(mark.subject)
            if not mark.is_occurred_at:
                tooltip_bits.append("enregistré")
            tooltip = escape_text(" — ".join(tooltip_bits))
            parts.append(
                f'<a href="{mark.href}"><text x="{x:.1f}" y="{y + 5:.1f}" '
                f'text-anchor="middle" class="{css_class}" '
                f'style="fill:{escape_text(mark.color)}" '
                f'font-size="{_MARK_FONT_SIZE}">'
                f"<title>{tooltip}</title>{escape_text(mark.shape)}</text></a>"
            )
            cursor_points.append(f'{{"x":{x:.2f},"href":"{mark.href}"}}')

        parts.append(
            f'<line x1="{x_of(instants[0]):.1f}" y1="0" '
            f'x2="{x_of(instants[0]):.1f}" y2="{height:.0f}" '
            'class="ribbon-cursor" style="display:none"></line>'
        )

    parts.append("</svg>")
    if cursor_points:
        parts.append(
            '<script type="application/json" id="ribbon-marks-data">'
            f'[{",".join(cursor_points)}]</script>'
        )

    return RibbonSvg(markup="".join(parts), mark_count=len(marks))
