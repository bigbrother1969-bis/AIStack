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

**Third slice, 2026-09-29 — production, applied, found two more real
gaps within hours of the second slice above.** The owner's own
screenshots of `/ribbon` after applying it: the whole page sits in a
900px-wide column no matter how wide the browser window is (a
heritage-wide convention, `console.html`/`architecture.html`/
`health.html` all cap themselves the same way — real, but not this
module's own doing), and — the one this module does own —
`docker-events` alone carried 49125 real instants in a ~4-hour window,
which the second slice's own clustering chained into a single glyph
labelled `"●49125"`, and `resource-priority-decision`'s own dozens of
smaller clusters sat close enough that their own multi-digit count
labels (`"22"`, `"3353"`) visually ran into each other even though the
underlying marks were already more than `_CLUSTER_MIN_GAP_PX` apart.
The owner read the second symptom as broken timestamps at first,
understandably — they are cluster counts, not instants, colliding.

Two real causes, not one: (1) `_CLUSTER_MIN_GAP_PX` was tuned against
a bare single glyph's own width, with no way to anticipate that a
cluster's own label grows wider once a multi-digit count is appended
to it; (2) nothing capped how large a single cluster could grow, so a
stream running two, three, four orders of magnitude denser than the
five-to-six-stream case this was designed against (§ above) collapses
into one glyph carrying a number, not a picture — the axis genuinely
has nothing more to say about `docker-events`' own shape at that
density, only about its total count and its own real first/last
instant.

The owner's own cadrage (`AskUserQuestion`, 2026-09-29) settled both,
together, as one patch: **(1) space clusters by their own real label
footprint**, not a fixed pixel gap — `_cluster_lane` now runs a second,
label-aware coalescing pass on top of its own first, position-only one
(unchanged), repeatedly merging adjacent clusters whose own estimated
rendered widths (`_estimated_label_width`, a deliberately conservative
per-character estimate — this module has no browser to ask for real
text metrics, the same "logic in `src/`, tested" constraint that keeps
this module framework-free) would still overlap once drawn. **(2) a
lane whose own clusters still cannot fit side by side inside the
available plot width even after that** — `docker-events`' own case —
renders as one honest summary badge instead: its real total count and
its real earliest/latest instant, still linking to a real `/node` (the
earliest member's), never a fabricated position and never a dead link.
Named here rather than left to discover: the summary badge's own `x`
is the midpoint of that lane's own real span, not a claim about where
"most" of its instants actually sit — at this density there is no
single honest point to draw.

Alongside this, `_VIEWBOX_WIDTH` grows from 900 to 1600 (the owner's
own broader decision, "toute la mini-app" — every Time Machine screen,
plus `console.html`/`architecture.html`/`health.html`, adapts to the
available window width rather than sitting in a fixed narrow column;
this module's own share of that is simply more logical drawing room
for every lane, directly easing the ordinary case this slice's own
label-footprint fix does not by itself reach).

**All the geometry lives here, pure and deterministic** (same
`RibbonMark`/`href`-arrives-pre-built contract
`aistack.renderers.timemachine.provenance_mermaid.ProvenanceNeighbor`
already holds), so it is testable by the governed suite without a
browser (`R5`: "toute la logique dans `src/`, testée ; couches web
minces"). `ribbon_view` in `timemachine_ui/app.py` calls
`render_ribbon_svg` with the same already-built `filtered` entries it
already renders as a flat list — kept, unremoved: the `dataviz`
skill's own non-negotiable, "a table view exists".

**Deliberately still narrower than the validated maquette** (re-measured
`claude/AUDIT-TIMEMACHINE-REALIGNEMENT-MAQUETTES-2026-10-02.md`, which
closed the fourth of four named gaps — cluster unfold, directly above
— one at a time with the owner, the remaining three kept open on
purpose, not forgotten): the network tree shown paired alongside the
ribbon (`/tree` stays a separate view — merging the two is real future
design); the event card's own "panneau Pourquoi" (1.7's own concern,
`ADR-0011` § 24 already named it); and the cursor itself only ever
opens the nearest instant's existing `/node` drill-down — it does not
reconstruct anything.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime

from aistack.renderers.text import escape_text

_VIEWBOX_WIDTH = 1600
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
# real visual gap between two distinguishable marks. This is the
# first, position-only clustering pass; the second, label-aware pass
# below (`_estimated_label_width`/`_LABEL_PADDING_PX`) is what actually
# keeps a cluster's own rendered count from overlapping its neighbour.
_CLUSTER_MIN_GAP_PX = 14.0

# No browser is available to this pure module to ask for a cluster's
# own real rendered text width (`R5`: logic in `src/`, tested without
# one) — this is a deliberately conservative per-character estimate
# for this heritage's own shared sans-serif stack at `_MARK_FONT_SIZE`,
# wide enough to be a safe over-, not under-, bound rather than a
# pixel-exact measurement.
_LABEL_CHAR_WIDTH_FACTOR = 0.62
_LABEL_PADDING_PX = 4.0

# See `_lane_needs_summary`'s own docstring: a single cluster this much
# larger than any close-in-time burst tested before 2026-09-29 (the
# largest deliberately tested, still one ordinary point, was 6; the
# smallest real production count cleanly on the other side of this
# line, found the same day, was 49125) no longer means a real pixel
# position, only a real total count.
_LANE_SUMMARY_MEMBER_THRESHOLD = 50


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


def _cluster_label_text(cluster: list[_Positioned]) -> str:
    """A cluster's own rendered glyph, its count suffix appended once
    there is more than one member — the exact text `_render_cluster`
    draws, shared here so the label-aware merge pass below reasons
    about the same string it will actually render, never a separate
    guess at what that string will be."""

    first = cluster[0].mark
    if len(cluster) > 1:
        return f"{first.shape}{len(cluster)}"
    return first.shape


def _estimated_label_width(text: str) -> float:
    """See `_LABEL_CHAR_WIDTH_FACTOR`'s own docstring: a conservative
    per-character estimate, not a real text metric."""

    return len(text) * _MARK_FONT_SIZE * _LABEL_CHAR_WIDTH_FACTOR


def _cluster_anchor_x(cluster: list[_Positioned]) -> float:
    return sum(item.x for item in cluster) / len(cluster)


def _clusters_would_overlap(a: list[_Positioned], b: list[_Positioned]) -> bool:
    """Would `a`'s own rendered label run into `b`'s once both are
    drawn at their own anchor — real production data (2026-09-29)
    found this happening between clusters already more than
    `_CLUSTER_MIN_GAP_PX` apart by raw position, once each one's own
    multi-digit count made its label wider than that fixed gap ever
    anticipated."""

    gap = abs(_cluster_anchor_x(b) - _cluster_anchor_x(a))
    required = (
        _estimated_label_width(_cluster_label_text(a)) / 2
        + _estimated_label_width(_cluster_label_text(b)) / 2
        + _LABEL_PADDING_PX
    )
    return gap < required


def _cluster_lane(positioned: list[_Positioned]) -> list[list[_Positioned]]:
    """
    Group one lane's own marks, already sorted by `x`, into clusters —
    two chained passes, not one.

    **First pass, position-only**: a run of consecutive marks each
    within `_CLUSTER_MIN_GAP_PX` of the previous one joins the same
    cluster, so three marks 5px apart each become one cluster of three
    even though the first and third are 28px apart — the same "too
    close to the one right next to it" reading a viewer's own eye would
    apply, not a fixed window around one fixed centre.

    **Second pass, label-aware** (2026-09-29): the first pass has no
    way to anticipate that a cluster's own rendered label grows wider
    once a multi-digit count is appended to it — two clusters can sit
    far enough apart by raw position to stay separate, yet still
    overlap once each one's own label text is actually drawn. This
    pass repeatedly merges adjacent clusters whose own estimated label
    footprints (`_clusters_would_overlap`) would still collide, until
    a full pass makes no further change — the same chained-merge idea
    as the first pass, one level up, on clusters instead of marks.
    """

    if not positioned:
        return []

    clusters: list[list[_Positioned]] = [[positioned[0]]]
    for item in positioned[1:]:
        if item.x - clusters[-1][-1].x < _CLUSTER_MIN_GAP_PX:
            clusters[-1].append(item)
        else:
            clusters.append([item])

    changed = True
    while changed:
        changed = False
        coalesced: list[list[_Positioned]] = []
        for cluster in clusters:
            if coalesced and _clusters_would_overlap(coalesced[-1], cluster):
                coalesced[-1] = coalesced[-1] + cluster
                changed = True
            else:
                coalesced.append(cluster)
        clusters = coalesced

    return clusters


def _lane_needs_summary(clusters: list[list[_Positioned]], plot_width: float) -> bool:
    """
    Does this lane's own picture stop being honest, even after both
    clustering passes above? Two independent reasons, either one
    enough on its own — real production data (2026-09-29) found one of
    each, on the same page, the same day:

    - **A single cluster has swallowed an abnormal share of the whole
      lane** (`_LANE_SUMMARY_MEMBER_THRESHOLD`). `docker-events`
      collapsed 49125 real instants into one glyph — a short,
      unremarkable-looking label (`"●49125"` is six characters; it
      fits the plot width many times over), which is exactly the
      trap: a short label reads as fine, but a single pixel position
      claiming to represent 49125 instants means nothing at that
      density. Counting each cluster's own label width can never catch
      this — digit count grows far slower than member count — so this
      is checked directly, on the raw member count, against a
      threshold far beyond any close-in-time burst this heritage
      tested before that (the largest deliberately tested, and still
      a single ordinary point, was 6).
    - **The lane's own clusters, laid out at their own minimum label
      spacing, no longer fit side by side** inside the available plot
      width. `resource-priority-decision`'s own case, the same day:
      dozens of individually small clusters whose own multi-digit
      count labels still ran into their neighbours' once there were
      enough of them.
    """

    if not clusters:
        return False

    if max(len(cluster) for cluster in clusters) > _LANE_SUMMARY_MEMBER_THRESHOLD:
        return True

    total = sum(
        _estimated_label_width(_cluster_label_text(cluster)) + _LABEL_PADDING_PX
        for cluster in clusters
    )
    return total > plot_width


def _render_lane_summary(
    lane_positioned: list[_Positioned], y: float, plot_left: float, plot_right: float
) -> tuple[str, str]:
    """
    One lane, too dense to plot honestly as individual points or
    clusters (`_lane_needs_summary`) — a single summary badge
    instead: the real total count and the real earliest/latest
    instant, drawn as a pill (a `<rect>` behind the `<text>`, the same
    "this is a count, not a position" visual language the ribbon's own
    foldable group counts already use) rather than a plain glyph, so it
    reads as clearly different from an ordinary mark or cluster. Its
    own `x` is the midpoint of this lane's own real span — not a claim
    that "most" instants sit there, simply where this lane's own data
    actually starts and ends on the shared axis. `href` still opens a
    real `/node` (the earliest member's) — never a fabricated position,
    never a dead link.
    """

    first = lane_positioned[0].mark
    instants = [item.instant for item in lane_positioned]
    earliest, latest = min(instants), max(instants)
    count = len(lane_positioned)
    any_gap = any(item.mark.is_gap for item in lane_positioned)
    css_class = "ribbon-mark ribbon-mark--summary ribbon-mark--gap" if any_gap else "ribbon-mark ribbon-mark--summary"

    lane_min_x = min(item.x for item in lane_positioned)
    lane_max_x = max(item.x for item in lane_positioned)
    x = min(max((lane_min_x + lane_max_x) / 2, plot_left), plot_right)

    label = f"{count} événements"
    label_width = _estimated_label_width(label)
    box_width = label_width + 12
    box_height = _MARK_FONT_SIZE + 8

    tooltip = escape_text(
        f"{first.stream} — {count} événements entre "
        f"{earliest.isoformat(timespec='seconds')} et "
        f"{latest.isoformat(timespec='seconds')}"
    )

    element = (
        f'<a href="{first.href}">'
        f'<rect x="{x - box_width / 2:.1f}" y="{y - box_height / 2:.1f}" '
        f'width="{box_width:.1f}" height="{box_height:.1f}" '
        f'rx="{box_height / 2:.1f}" class="ribbon-mark-summary-box"></rect>'
        f'<text x="{x:.1f}" y="{y + 4:.1f}" text-anchor="middle" '
        f'class="{css_class}" style="fill:{escape_text(first.color)}" '
        f'font-size="{_MARK_FONT_SIZE - 2}">'
        f"<title>{tooltip}</title>{escape_text(label)}</text></a>"
    )
    # No `members` key here — deliberate, unchanged from the cadrage
    # that created this function (2026-09-29): a summary badge already
    # stands for a count too large to plot honestly point by point
    # (`_lane_needs_summary`'s own docstring, "a single pixel position
    # claiming to represent 49125 instants means nothing"); unfolding
    # it into a clickable list would reproduce exactly the illegible
    # density this badge exists to replace. Scoped out of the 2026-10-02
    # cluster-unfold cadrage (`AskUserQuestion`, "laisser tels quels"),
    # named here rather than left to discover.
    cursor_point = json.dumps(
        {"x": round(x, 2), "y": round(y, 2), "href": first.href},
        separators=(",", ":"),
    )
    return element, cursor_point


def _render_cluster(cluster: list[_Positioned], y: float) -> tuple[str, str]:
    """
    One cluster's own `<a><text>...` element, plus its own JSON cursor
    point. A single-member cluster renders exactly as § 24's original
    single-mark case; a multi-member cluster keeps the lane's own
    colour/shape (every member shares it — one lane is one stream) and
    appends its own count, never averaging or dropping a member's own
    instant out of the tooltip.

    **"Déplier sur place" (2026-10-02, owner cadrage, `AskUserQuestion`:
    "liste déroulante au clic", not a spatial fan-out on the axis) —
    the cursor point a multi-member cluster hands the page's own script
    now carries its own `members` list, one entry per instant, each with
    its own real `href` (never only the earliest member's, unlike the
    glyph's own `<a>` above, kept unchanged for the no-JS case). The
    script draws these as a small list next to the glyph instead of
    navigating straight to the earliest member — the same "never a
    fabricated position, never a dead link" discipline this module
    already holds, extended to every member, not only the first. A
    single-member cluster carries no `members` key at all — nothing to
    unfold, the same restraint `_render_lane_summary` already applies
    for the opposite reason (too many members to unfold honestly).
    """

    first = cluster[0].mark
    x = _cluster_anchor_x(cluster)
    any_gap = any(item.mark.is_gap for item in cluster)
    css_class = "ribbon-mark ribbon-mark--gap" if any_gap else "ribbon-mark"
    if len(cluster) > 1:
        css_class += " ribbon-mark--cluster"
    glyph = _cluster_label_text(cluster)

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
    point_data: dict[str, object] = {
        "x": round(x, 2),
        "y": round(y, 2),
        "href": first.href,
    }
    if len(cluster) > 1:
        point_data["members"] = [
            {
                "href": item.mark.href,
                "instant": item.instant.isoformat(timespec="seconds"),
                "subject": item.mark.subject,
                "is_occurred_at": item.mark.is_occurred_at,
                "is_gap": item.mark.is_gap,
            }
            for item in cluster
        ]
    cursor_point = json.dumps(point_data, separators=(",", ":"))
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
            if not lane_marks:
                continue
            clusters = _cluster_lane(lane_marks)
            if not _lane_needs_summary(clusters, plot_right - plot_left):
                for cluster in clusters:
                    element, cursor_point = _render_cluster(cluster, lane_y[stream])
                    parts.append(element)
                    cursor_points.append(cursor_point)
                    if first_x is None:
                        first_x = cluster[0].x
            else:
                element, cursor_point = _render_lane_summary(
                    lane_marks, lane_y[stream], plot_left, plot_right
                )
                parts.append(element)
                cursor_points.append(cursor_point)
                if first_x is None:
                    first_x = lane_marks[0].x

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
