"""`aistack.selection.screen.status_message` — what the screen says after a save."""

from __future__ import annotations

from aistack.generators.filesystem.hardlink import MaterialisationReport
from aistack.i18n import translator_for
from aistack.selection.screen import status_message

T = translator_for("en")


def test_a_refusal_is_said_as_it_is():
    report = MaterialisationReport(refused="the selection exceeds the declared quota")

    assert status_message(report, 3, T) == "the selection exceeds the declared quota"


def test_nothing_changed_reads_as_up_to_date():
    assert status_message(MaterialisationReport(unchanged=4), 2, T) == T(
        "selection.status.up_to_date", count=2
    )


def test_a_change_counts_every_kind():
    report = MaterialisationReport(linked=("a", "b"), removed=("c",), pruned=("d",))

    assert status_message(report, 5, T) == T(
        "selection.status.changed", count=5, linked=2, relinked=0, removed=1, pruned=1
    )
