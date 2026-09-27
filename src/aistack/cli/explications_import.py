from __future__ import annotations

from aistack.explications import import_explain_answers


def main() -> None:
    """
    Import the AI Runtime's own `explain` answers as Explications
    (`ADR-0011` § *Decision* 8) — the first of the four real sources
    that ADR names, run explicitly rather than folded into
    `aistack.cli.timemachine_rebuild`: importing raw source material
    into governed Explications is a deliberate act (the owner's own
    decision, 2026-09-27, on which sources enter and at what
    confidence), not something every graph rebuild should silently
    redo. `timemachine_rebuild` only ever projects what this command
    (and its siblings — `aistack.cli.explications_import_pra_tests`,
    with the remaining two still to come) has already recorded — the
    same "collect, then project" split every other historicised
    stream already keeps between its own collector and the Time
    Machine's read side.

    Idempotent: running this twice without new AI Reasoning History
    activity records nothing new the second time
    (`import_explain_answers`'s own docstring).
    """

    summary = import_explain_answers()

    print("Explications Import — AI Runtime explain answers")
    print(f"- Subjects seen: {summary.subjects_seen}")
    print(f"- Explain answers seen: {summary.explain_answers_seen}")
    print(f"- Explications recorded: {summary.explications_recorded}")
    print(f"- Already imported (skipped): {summary.explications_already_imported}")


if __name__ == "__main__":
    main()
