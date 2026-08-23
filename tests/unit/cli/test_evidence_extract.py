from aistack.cli.runtime_diagnose import EVIDENCE_WIDTH, extract


LONG = "x" * 1000


def test_a_line_that_fits_is_returned_whole():

    line = "AUTH_FAILED " + "x" * 50

    assert extract(line, 0) == line


def test_a_line_exactly_the_width_is_not_cut():

    line = "y" * EVIDENCE_WIDTH

    assert extract(line, 0) == line


def test_the_window_is_centred_on_the_match():
    """
    The whole reason this exists. An extract taken from the start
    shows the pattern only when the pattern is near the start,
    which is a property of the log and not of the rule.
    """

    line = LONG + "AUTH_FAILED" + LONG

    shown = extract(line, 1000)

    assert "AUTH_FAILED" in shown
    assert shown.index("AUTH_FAILED") > 20
    assert shown.index("AUTH_FAILED") < EVIDENCE_WIDTH


def test_context_is_shown_on_both_sides_of_the_match():
    """
    A window ending at the match would show what fired the rule
    and nothing of what surrounded it — and the surroundings are
    what a reader uses to decide whether the finding matters.
    """

    line = "a" * 1000 + "AUTH_FAILED" + "b" * 1000

    shown = extract(line, 1000)

    assert "aaaAUTH_FAILEDbbb" in shown


def test_what_is_cut_is_counted_on_each_side():
    """
    The heritage refuses to trim the number of evidence lines in
    silence; the same applies inside a line. A bare ellipsis would
    misplace the match in the reader's head.
    """

    line = LONG + "AUTH_FAILED" + LONG

    shown = extract(line, 1000)

    assert "cut] …" in shown
    assert "… [" in shown


def test_a_match_near_the_start_wastes_no_window():

    line = "AUTH_FAILED" + LONG

    shown = extract(line, 0)

    assert shown.startswith("AUTH_FAILED")
    assert "cut] …" not in shown
    assert shown.endswith("cut]")


def test_a_match_near_the_end_wastes_no_window():
    """
    Kills the mutant that removes the re-clamp: without it the
    window runs past the end of the line, the extract comes back
    shorter than the width, and the trailing counter goes
    negative — a report claiming a negative number of hidden
    characters.
    """

    line = LONG + "AUTH_FAILED"

    shown = extract(line, len(line) - len("AUTH_FAILED"))

    assert shown.endswith("AUTH_FAILED")
    assert "…" in shown
    assert "-" not in shown.split("cut]")[0]

    body = shown.split("] …", 1)[1]

    assert len(body) == EVIDENCE_WIDTH


def test_the_counters_add_up_to_the_line():
    """
    A reader who adds the two numbers to the extract's length must
    get the line back. Anything else means the report is hiding a
    different amount than it says.
    """

    line = LONG + "AUTH_FAILED" + LONG

    shown = extract(line, 1000)

    head = int(shown.split(" cut]", 1)[0].lstrip("["))
    tail = int(shown.rsplit("[", 1)[1].split(" cut]", 1)[0])
    body = shown.split("] …", 1)[1].rsplit("… [", 1)[0]

    assert head + len(body) + tail == len(line)


def test_an_undetermined_position_falls_back_to_the_start():
    """
    `match_at` of `None` means the pattern is present and its
    position could not be determined. Centring on a position
    nobody computed would put the window somewhere arbitrary and
    call it evidence.
    """

    line = LONG + "AUTH_FAILED" + LONG

    shown = extract(line, None)

    assert shown.startswith("xxx")
    assert not shown.startswith("[")
    assert shown.endswith(f"[+{len(line) - EVIDENCE_WIDTH}]")
