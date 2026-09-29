from __future__ import annotations

from datetime import datetime, timedelta, timezone

from aistack.renderers.timemachine import RibbonMark, render_ribbon_svg
from aistack.renderers.timemachine.ribbon_svg import _Positioned, _lane_needs_summary


def mark(
    href: str = "/node?iri=urn%3Aaistack%3Adocker-events%3Ajellyfin&lang=fr",
    stream: str = "docker-events",
    instant: str = "2026-09-28T10:00:00+00:00",
    subject: str | None = "jellyfin",
    is_gap: bool = False,
    is_occurred_at: bool = True,
    color: str = "#2f6fed",
    shape: str = "●",
) -> RibbonMark:
    return RibbonMark(
        href=href,
        stream=stream,
        instant=instant,
        subject=subject,
        is_gap=is_gap,
        is_occurred_at=is_occurred_at,
        color=color,
        shape=shape,
    )


def test_no_streams_and_no_marks_still_renders_a_real_axis_not_a_crash():
    result = render_ribbon_svg((), ())

    assert result.mark_count == 0
    assert "<svg" in result.markup
    assert 'class="ribbon-axis-line"' in result.markup
    assert "ribbon-marks-data" not in result.markup


def test_streams_with_every_box_unchecked_render_lanes_but_no_marks():
    result = render_ribbon_svg((), ("docker-events", "docker-diff"))

    assert result.mark_count == 0
    assert result.markup.count('class="ribbon-lane-line"') == 2
    assert "docker-events" in result.markup
    assert "docker-diff" in result.markup


def test_a_single_mark_is_placed_at_the_lane_midpoint_with_no_division_by_zero():
    result = render_ribbon_svg((mark(),), ("docker-events",))

    assert result.mark_count == 1
    assert 'class="ribbon-mark"' in result.markup
    assert 'href="/node?iri=urn%3Aaistack%3Adocker-events%3Ajellyfin&lang=fr"' in result.markup


def test_two_marks_on_the_same_stream_land_on_the_same_lane_line():
    early = mark(instant="2026-09-28T09:00:00+00:00", href="/node?iri=a")
    later = mark(instant="2026-09-28T11:00:00+00:00", href="/node?iri=b")

    result = render_ribbon_svg((early, later), ("docker-events",))

    assert result.mark_count == 2
    # Exactly one lane line was drawn even though two marks share it.
    assert result.markup.count('class="ribbon-lane-line"') == 1


def test_marks_on_different_streams_keep_their_own_lane_order():
    first = mark(stream="docker-diff", href="/node?iri=diff")
    second = mark(stream="docker-events", href="/node?iri=events")

    result = render_ribbon_svg(
        (first, second), ("docker-diff", "docker-events")
    )

    diff_lane_index = result.markup.index("docker-diff")
    events_lane_index = result.markup.index("docker-events")
    assert diff_lane_index < events_lane_index


def test_the_earliest_and_latest_instant_both_get_an_axis_label():
    early = mark(instant="2026-09-28T09:00:00+00:00", href="/node?iri=a")
    later = mark(instant="2026-09-28T11:00:00+00:00", href="/node?iri=b")

    result = render_ribbon_svg((early, later), ("docker-events",))

    assert "2026-09-28T09:00:00" in result.markup
    assert "2026-09-28T11:00:00" in result.markup


def test_all_marks_at_the_identical_instant_do_not_divide_by_zero():
    same_time = "2026-09-28T09:00:00+00:00"
    one = mark(instant=same_time, href="/node?iri=a")
    two = mark(instant=same_time, href="/node?iri=b")

    result = render_ribbon_svg((one, two), ("docker-events",))

    assert result.mark_count == 2
    assert "<svg" in result.markup


def test_a_gap_entry_gets_its_own_css_class_and_says_so_in_its_tooltip():
    result = render_ribbon_svg((mark(is_gap=True),), ("docker-events",))

    assert "ribbon-mark--gap" in result.markup


def test_a_recording_time_fallback_is_named_in_the_tooltip_never_presented_as_occurred():
    result = render_ribbon_svg((mark(is_occurred_at=False),), ("docker-events",))

    assert "enregistré" in result.markup


def test_marks_emit_a_json_data_island_for_the_cursor_script():
    result = render_ribbon_svg((mark(),), ("docker-events",))

    assert '<script type="application/json" class="ribbon-marks-data">' in result.markup
    assert '"href":"/node?iri=urn%3Aaistack%3Adocker-events%3Ajellyfin&lang=fr"' in result.markup


def test_a_stream_name_with_markup_characters_is_escaped_in_the_lane_label():
    result = render_ribbon_svg((), ("<script>evil</script>",))

    assert "<script>evil</script>" not in result.markup
    assert "&lt;script&gt;" in result.markup


# --- Clustering (ADR-0011 §26's second slice, 2026-09-29) -----------
#
# Real production data (the owner's own screenshot) showed instants a
# few seconds apart on the same lane rendering as one illegible smear
# at this module's own time scale — these tests pin exact instants
# (seconds apart, well under the real axis's own hours/days span) to
# force clustering deterministically, the same frozen-instant
# discipline `test_project_upgrade_correlation.py` already established
# for precise nearest-neighbour verification.


def test_two_marks_one_second_apart_on_a_day_long_axis_merge_into_one_cluster():
    close_one = mark(instant="2026-09-28T09:00:00+00:00", href="/node?iri=a")
    close_two = mark(instant="2026-09-28T09:00:01+00:00", href="/node?iri=b")
    far = mark(instant="2026-09-29T09:00:00+00:00", href="/node?iri=c")

    result = render_ribbon_svg((close_one, close_two, far), ("docker-events",))

    assert result.mark_count == 3
    assert "ribbon-mark--cluster" in result.markup
    # The cluster's own glyph carries its member count.
    assert f"{close_one.shape}2" in result.markup
    # Only two cursor points: one for the two-member cluster, one for
    # the far mark that stayed on its own.
    assert result.markup.count('"href"') == 2


def test_a_clustered_mark_still_names_every_member_in_its_tooltip():
    close_one = mark(instant="2026-09-28T09:00:00+00:00", href="/node?iri=a", subject="jellyfin")
    close_two = mark(instant="2026-09-28T09:00:01+00:00", href="/node?iri=b", subject="arrstack")
    far = mark(instant="2026-09-29T09:00:00+00:00", href="/node?iri=c", subject=None)

    result = render_ribbon_svg((close_one, close_two, far), ("docker-events",))

    assert "ribbon-mark--cluster" in result.markup
    assert "jellyfin" in result.markup
    assert "arrstack" in result.markup


def test_a_cluster_still_navigates_to_a_real_node_never_a_dead_link():
    close_one = mark(instant="2026-09-28T09:00:00+00:00", href="/node?iri=earliest")
    close_two = mark(instant="2026-09-28T09:00:01+00:00", href="/node?iri=latest")
    far = mark(instant="2026-09-29T09:00:00+00:00", href="/node?iri=far")

    result = render_ribbon_svg((close_one, close_two, far), ("docker-events",))

    assert "ribbon-mark--cluster" in result.markup
    assert 'href="/node?iri=earliest"' in result.markup


def test_marks_far_apart_on_a_short_axis_do_not_cluster():
    early = mark(instant="2026-09-28T09:00:00+00:00", href="/node?iri=a")
    later = mark(instant="2026-09-28T09:10:00+00:00", href="/node?iri=b")

    result = render_ribbon_svg((early, later), ("docker-events",))

    assert "ribbon-mark--cluster" not in result.markup
    assert result.markup.count('"href"') == 2


def test_a_cluster_containing_a_gap_still_gets_the_gap_css_class():
    normal = mark(instant="2026-09-28T09:00:00+00:00", href="/node?iri=a", is_gap=False)
    gap = mark(instant="2026-09-28T09:00:01+00:00", href="/node?iri=b", is_gap=True)
    far = mark(instant="2026-09-29T09:00:00+00:00", href="/node?iri=c", is_gap=False)

    result = render_ribbon_svg((normal, gap, far), ("docker-events",))

    assert "ribbon-mark--gap" in result.markup
    assert "ribbon-mark--cluster" in result.markup


# --- Third slice (ADR-0011 §26, production found two more real gaps
# within hours of the second slice, 2026-09-29) -----------------------
#
# Real production data: `docker-events` collapsed 49125 real instants
# into one glyph labelled "●49125" (no useful position left at all),
# and `resource-priority-decision`'s dozens of small clusters had
# multi-digit count labels ("22", "3353") visually running into their
# neighbours' even though the underlying marks stayed more than
# `_CLUSTER_MIN_GAP_PX` apart. The owner read the second symptom as
# broken timestamps at first — they are cluster counts colliding, not
# instants.


def _iso(base: datetime, seconds: float) -> str:
    return (base + timedelta(seconds=seconds)).isoformat()


def test_clusters_more_than_min_gap_apart_still_merge_once_their_own_multi_digit_labels_would_overlap():
    # Two eleven-member bursts (each chains into its own "●11" cluster
    # under the first, position-only pass — an 11px-wide run each) with
    # a 15px gap between them: more than `_CLUSTER_MIN_GAP_PX` (14), so
    # the first pass alone would keep them apart. Once each carries its
    # own two-digit count, their labels are wide enough that they still
    # visually overlap at that distance — the second, label-aware pass
    # is what merges them into one "●22".
    base = datetime(2026, 9, 28, 9, 0, 0, tzinfo=timezone.utc)

    earliest = mark(instant=_iso(base, 0), href="/node?iri=earliest")
    cluster_a = [mark(instant=_iso(base, 500 + i), href=f"/node?iri=a{i}") for i in range(11)]
    cluster_b = [mark(instant=_iso(base, 525 + i), href=f"/node?iri=b{i}") for i in range(11)]
    latest = mark(instant=_iso(base, 1430), href="/node?iri=latest")

    result = render_ribbon_svg((earliest, *cluster_a, *cluster_b, latest), ("docker-events",))

    assert result.mark_count == 24
    assert "ribbon-mark--cluster" in result.markup
    assert "●22" in result.markup
    assert "●11" not in result.markup
    # Three cursor points: the lone earliest mark, the merged 22-member
    # cluster, and the lone latest mark — never four (A and B staying
    # separate) and never two (the lone marks joining in too).
    assert result.markup.count('"href"') == 3


def test_a_lane_with_an_abnormally_large_cluster_renders_one_honest_summary_instead():
    # A 60-member burst — comfortably past `_LANE_SUMMARY_MEMBER_
    # THRESHOLD` (50), the same order-of-magnitude jump `docker-events`
    # showed in production (49125) — collapses the whole lane (all 62
    # marks, not just the burst) into one summary badge rather than one
    # illegible mega-cluster glyph.
    base = datetime(2026, 9, 28, 9, 0, 0, tzinfo=timezone.utc)

    earliest = mark(instant=_iso(base, 0), href="/node?iri=earliest")
    burst = [mark(instant=_iso(base, 700 + i), href=f"/node?iri=burst{i}") for i in range(60)]
    latest = mark(instant=_iso(base, 1430), href="/node?iri=latest")

    result = render_ribbon_svg((earliest, *burst, latest), ("docker-events",))

    assert result.mark_count == 62
    assert "ribbon-mark--summary" in result.markup
    assert "62 événements" in result.markup
    assert 'href="/node?iri=earliest"' in result.markup
    # One picture element for the whole lane — never 62 individual
    # points, and never a giant illegible cluster glyph either.
    assert result.markup.count('"href"') == 1


def _bare_cluster(member_count: int) -> list[_Positioned]:
    """A cluster with no real spread of instants — `_lane_needs_summary`
    and the helpers it calls only ever read a cluster's own member
    count and its rendered label width, never its `x`, so constructing
    this through `render_ribbon_svg`'s own public, timestamp-driven
    positioning would mean packing clusters to within a pixel of their
    own minimum non-overlap spacing: a genuinely fragile, boundary-
    precision reconstruction for what this is — a plain sum comparison.
    Testing the private geometry helper directly, as this heritage
    already does elsewhere when the alternative is that fragile, is
    the more honest test (`R5`)."""

    instant = datetime(2026, 9, 28, 9, 0, 0, tzinfo=timezone.utc)
    m = mark(instant=instant.isoformat())
    return [_Positioned(x=0.0, instant=instant, mark=m) for _ in range(member_count)]


def test_many_individually_reasonable_clusters_still_overflow_the_available_width():
    # 70 two-member clusters ("●2" each, far under the 50-member
    # threshold on their own) still add up to more label footprint
    # than a 1430px plot has room for — `resource-priority-decision`'s
    # own real shape: no single cluster is abnormal, but there are too
    # many of them to lay out side by side without their labels
    # colliding.
    clusters = [_bare_cluster(2) for _ in range(70)]

    assert _lane_needs_summary(clusters, plot_width=1430.0) is True


def test_a_handful_of_well_separated_small_clusters_fit_comfortably():
    clusters = [_bare_cluster(2) for _ in range(5)]

    assert _lane_needs_summary(clusters, plot_width=1430.0) is False
