from __future__ import annotations

from aistack.renderers.timemachine import RibbonMark, render_ribbon_svg


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

    assert '<script type="application/json" id="ribbon-marks-data">' in result.markup
    assert '"href":"/node?iri=urn%3Aaistack%3Adocker-events%3Ajellyfin&lang=fr"' in result.markup


def test_a_stream_name_with_markup_characters_is_escaped_in_the_lane_label():
    result = render_ribbon_svg((), ("<script>evil</script>",))

    assert "<script>evil</script>" not in result.markup
    assert "&lt;script&gt;" in result.markup
