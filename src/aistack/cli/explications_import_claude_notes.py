from __future__ import annotations

from aistack.explications import import_claude_notes


def main() -> None:
    """
    Import the project's own `claude/*.md` session notes as
    Explications (`ADR-0011` § *Decision* 8) — the third of the four
    real sources that ADR names, and the second of
    `aistack.cli.explications_import`'s own "siblings". A separate
    command, not a flag on either of the first two: importing a
    source is the owner's own deliberate act per source.

    Idempotent by content hash, not by date: running this twice
    without an edited note records nothing new the second time
    (`import_claude_notes`'s own docstring).
    """

    summary = import_claude_notes()

    print("Explications Import — claude/ session notes")
    print(f"- Notes seen: {summary.notes_seen}")
    print(f"- Notes skipped (no subject or date): {summary.notes_skipped}")
    print(f"- Explications recorded: {summary.explications_recorded}")
    print(f"- Already imported (skipped): {summary.explications_already_imported}")


if __name__ == "__main__":
    main()
