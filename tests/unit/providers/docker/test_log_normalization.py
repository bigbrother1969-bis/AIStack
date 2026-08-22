from datetime import datetime, timezone

import pytest

from aistack.providers.docker import DockerProvider
from aistack.providers.docker.log_normalization import (
    normalize_log_evidence,
)


NOW = datetime(2026, 8, 22, 12, 0, 0, tzinfo=timezone.utc)


def normalize(raw: str, depth: int = 100):
    return normalize_log_evidence(
        raw,
        subject="gluetun",
        provider="aistack.provider.docker",
        state="running",
        depth=depth,
        collected_at=NOW,
    )


def test_offsets_count_back_from_the_newest_line():
    """
    A reader asks how far back something appeared, not which
    index it held in a window whose start moves with every new
    line.
    """

    observation = normalize("oldest\nmiddle\nnewest\n")

    assert [(e.offset, e.text) for e in observation.entries] == [
        (2, "oldest"),
        (1, "middle"),
        (0, "newest"),
    ]


def test_the_terminating_newline_is_not_a_line():
    """
    `docker logs` ends its output with a newline. Splitting on it
    yields a trailing empty element no container ever printed.
    """

    assert len(normalize("one\ntwo\n").entries) == 2
    assert len(normalize("one\ntwo").entries) == 2


def test_no_output_yields_an_observation_with_no_entries():
    """
    "Nothing was printed" is a fact about the subject. Returning
    nothing would make it indistinguishable from "nothing was
    looked at".
    """

    observation = normalize("")

    assert observation.entries == ()
    assert observation.subject == "gluetun"
    assert observation.depth == 100


def test_lines_are_kept_verbatim():
    """
    No trimming, no case folding, no filtering. A signature that
    matched a line the pipeline had reworded would cite something
    that never appeared on the host — and comparison is the
    qualifier's business, declared per rule by
    `Signature.case_sensitive`.
    """

    raw = "  Your credentials might be WRONG  \n\tTLS Error\n"

    assert [e.text for e in normalize(raw).entries] == [
        "  Your credentials might be WRONG  ",
        "\tTLS Error",
    ]


def test_an_empty_line_between_two_others_is_a_line():

    observation = normalize("first\n\nthird\n")

    assert [e.text for e in observation.entries] == ["first", "", "third"]


def test_the_observation_carries_the_depth_that_was_asked_for():
    """
    A signature declaring a window deeper than what was collected
    cannot fire. Without the depth travelling alongside, *absent*
    and *out of range* would be the same result.
    """

    assert normalize("one\n", depth=2000).depth == 2000


def test_more_lines_than_depth_is_refused_by_the_contract():
    """
    `docker logs --tail N` returns at most N lines. If it ever
    returned more, the observation would be describing a window
    it did not read, and the contract refuses to exist.
    """

    with pytest.raises(ValueError, match="depth"):
        normalize("one\ntwo\nthree\n", depth=2)


def test_collecting_no_lines_is_refused_before_docker_is_called():
    """
    Reached without a Docker daemon: the guard precedes the
    subprocess call.
    """

    with pytest.raises(ValueError, match="observes nothing"):
        DockerProvider().collect_logs("gluetun", 0, "running")


def test_the_observation_names_the_provider_that_produced_it():

    assert normalize("x\n").provider == "aistack.provider.docker"


# --------------------------------------------------------------------
# The timestamp Docker prefixes is a field, not part of the line
# --------------------------------------------------------------------


def test_the_docker_timestamp_prefix_is_split_off_the_text():
    """
    `docker logs --timestamps` prefixes each line. Left inside
    the text, every signature would compare against something no
    container printed.
    """

    entry = normalize("2026-08-22T09:41:12.000000000Z TLS Error\n").entries[0]

    assert entry.text == "TLS Error"
    assert entry.timestamp == datetime(
        2026, 8, 22, 9, 41, 12, tzinfo=timezone.utc
    )


def test_a_pattern_cannot_match_the_prefix_the_collector_added():
    """
    The concrete failure the split prevents: a signature looking
    for a four-digit year, or for `Z`, would fire on every line
    of every container and cite evidence the host never emitted.
    """

    entries = normalize(
        "2026-08-22T09:41:12.000000000Z all quiet\n"
        "2026-08-22T09:41:13.000000000Z still quiet\n"
    ).entries

    assert not any("2026" in e.text for e in entries)


def test_nanoseconds_are_truncated_rather_than_refused():
    """
    Docker writes nine fractional digits; `datetime` carries six.
    Truncating loses a resolution nothing here uses. Refusing
    would lose the age of every line.
    """

    entry = normalize("2026-08-22T09:41:12.123456789Z x\n").entries[0]

    assert entry.timestamp.microsecond == 123456
    assert entry.text == "x"


def test_a_line_whose_prefix_does_not_parse_is_kept_whole():
    """
    Collection without `--timestamps`, or a malformed prefix.
    The honest result is "the age is unknown" — a state — not a
    fabricated time and not a truncated line.
    """

    entry = normalize("Your credentials might be wrong\n").entries[0]

    assert entry.timestamp is None
    assert entry.text == "Your credentials might be wrong"


def test_an_unparsable_prefix_does_not_lose_the_first_word():

    entry = normalize("AUTH_FAILED reported by the peer\n").entries[0]

    assert entry.text == "AUTH_FAILED reported by the peer"


def test_a_timestamped_line_that_is_otherwise_empty_is_an_empty_line():

    entry = normalize("2026-08-22T09:41:12.000000000Z \n").entries[0]

    assert entry.text == ""
    assert entry.timestamp is not None
