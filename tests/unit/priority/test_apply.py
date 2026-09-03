"""
`ApplyReport.changed` — the one condition `log_cycle` (printing) and
`aistack.priority.decision_history.record_decision` (CPU decision
history, 2026-09-03) both trigger on, kept as a single property so
neither can drift from the other.

`apply_resource_priority` itself stays untested here, per decision
#9 — host-touching (`docker inspect`/`docker update`), verified live
rather than in the governed suite.
"""

from __future__ import annotations

from aistack.priority.apply import ApplyReport


def test_unchanged_alone_is_not_a_change():
    report = ApplyReport(unchanged=("jellyfin", "radarr"))

    assert report.changed is False


def test_nothing_at_all_is_not_a_change():
    assert ApplyReport().changed is False


def test_applied_is_a_change():
    assert ApplyReport(applied=("jellyfin",)).changed is True


def test_failed_is_a_change():
    assert ApplyReport(failed=(("jellyfin", "permission denied"),)).changed is True


def test_not_found_is_a_change():
    """
    A container the owner removed is not `failed`, but it is still
    worth surfacing — the same distinction `ApplyReport`'s own
    docstring draws for `not_found is not failed`, extended here to
    what counts as worth printing or persisting.
    """

    assert ApplyReport(not_found=("radarr",)).changed is True


def test_unchanged_alongside_a_real_change_is_still_a_change():
    report = ApplyReport(applied=("jellyfin",), unchanged=("radarr",))

    assert report.changed is True
