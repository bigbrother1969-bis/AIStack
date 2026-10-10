"""The Time Machine's time ribbon as SVG (ADR-0011 § 26): a horizontal time
axis with one lane per stream.

SVG plus a little inline JavaScript, no library: the page stays
self-contained. Clicking or releasing a drag of the cursor opens the
nearest instant's `/node` card; dragging only previews, so the browser is
not asked to navigate on every `mousemove`. Hover uses SVG's native
`<title>` tooltips.

Dense lanes are handled in three steps:

1. Marks too close to tell apart merge into a counted cluster (`"●3"`)
   whose tooltip lists every member and whose script data lets the page
   unfold it into a list of links.
2. Clusters whose labels would overlap are merged again, using an
   estimated label width (no browser is available to measure text).
3. A lane still too dense (one huge cluster, or labels that cannot fit
   the plot width) becomes a single summary badge: total count and
   first/last instant, placed at the middle of the lane's span.

Pure and deterministic; `href`s arrive pre-built. The caller
(`aistack.timemachine.screen`) keeps a flat list of the same entries
beneath the graphic as the accessible table view.
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

# First clustering pass: marks on one lane closer than this cannot be told
# apart at `_MARK_FONT_SIZE`. The label-aware pass below keeps cluster
# counts from overlapping.
_CLUSTER_MIN_GAP_PX = 14.0

# Conservative per-character width estimate for the sans-serif stack at
# `_MARK_FONT_SIZE`; an over-estimate on purpose, since no browser can measure.
_LABEL_CHAR_WIDTH_FACTOR = 0.62
_LABEL_PADDING_PX = 4.0

# A cluster larger than this no longer stands for a pixel position, only a
# count; see `_lane_needs_summary`.
_LANE_SUMMARY_MEMBER_THRESHOLD = 50


@dataclass(frozen=True)
class RibbonMark:
    """One instant to place on the ribbon; `href`, `color` and `shape` arrive pre-built.

    `instant` is a `datetime.isoformat()` string, the form every projector
    writes, so `datetime.fromisoformat` parses it exactly.
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
    """The rendered SVG markup and how many marks it holds."""

    markup: str
    mark_count: int


@dataclass(frozen=True)
class _Positioned:
    """One mark placed on the time axis; the unit `_cluster_lane` groups."""

    x: float
    instant: datetime
    mark: RibbonMark


def _parse(instant: str) -> datetime:
    return datetime.fromisoformat(instant)


def _cluster_label_text(cluster: list[_Positioned]) -> str:
    """The glyph a cluster renders, with its member count when there are several.

    Shared with the overlap check so both reason about the same text.
    """

    first = cluster[0].mark
    if len(cluster) > 1:
        return f"{first.shape}{len(cluster)}"
    return first.shape


def _estimated_label_width(text: str) -> float:
    """Conservative estimated width of a label, not a real text metric."""

    return len(text) * _MARK_FONT_SIZE * _LABEL_CHAR_WIDTH_FACTOR


def _cluster_anchor_x(cluster: list[_Positioned]) -> float:
    return sum(item.x for item in cluster) / len(cluster)


def _clusters_would_overlap(a: list[_Positioned], b: list[_Positioned]) -> bool:
    """Whether `a`'s and `b`'s labels would overlap at their anchors."""

    gap = abs(_cluster_anchor_x(b) - _cluster_anchor_x(a))
    required = (
        _estimated_label_width(_cluster_label_text(a)) / 2
        + _estimated_label_width(_cluster_label_text(b)) / 2
        + _LABEL_PADDING_PX
    )
    return gap < required


def _cluster_lane(positioned: list[_Positioned]) -> list[list[_Positioned]]:
    """Group one lane's marks, sorted by `x`, into clusters in two passes.

    First pass, position only: consecutive marks each within
    `_CLUSTER_MIN_GAP_PX` of the previous join the same cluster (chained,
    not a fixed window). Second pass: adjacent clusters whose estimated
    labels would overlap are merged repeatedly until nothing changes, since
    a multi-digit count widens a label beyond the first pass's gap.
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
    """Whether a lane must be drawn as a summary badge instead of clusters.

    Either one cluster exceeds `_LANE_SUMMARY_MEMBER_THRESHOLD` members (its
    label stays short, but one position for thousands of instants means
    nothing), or the clusters' labels do not fit side by side in `plot_width`.
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
    """One lane too dense to plot, drawn as a summary badge.

    A pill with the total count and the first/last instants, at the middle
    of the lane's real span (not a claim about where most instants sit).
    It links to the earliest member's `/node`.
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
    # No `members` list here: unfolding a summary badge would bring back the
    # density it replaces.
    cursor_point = json.dumps(
        {"x": round(x, 2), "y": round(y, 2), "href": first.href},
        separators=(",", ":"),
    )
    return element, cursor_point


def _render_cluster(cluster: list[_Positioned], y: float) -> tuple[str, str]:
    """One cluster's `<a><text>` element and its JSON cursor point.

    A multi-member cluster keeps the lane's colour and shape, appends its
    count, and lists every member in its tooltip. Its cursor point carries a
    `members` list, each with its own `href`, which the page script shows as
    a list on click; the `<a>` still opens the earliest member without
    JavaScript. A single-member cluster has no `members` key.
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
    """Render every mark on a time axis, one lane per stream in the given order.

    Lanes never reorder when a filter hides another stream. Deterministic.
    An empty `marks` still renders the axis and the lanes.
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
