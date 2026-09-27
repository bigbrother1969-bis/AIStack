from __future__ import annotations

from aistack.explications import import_pra_tests_comments


def main() -> None:
    """
    Import `pra_tests.yml`'s own dated comments as Explications
    (`ADR-0011` § *Decision* 8) — the second of the four real sources
    that ADR names, and the first of `aistack.cli.explications_import`'s
    own "siblings, still to come" (that command's own docstring). A
    separate command, not a flag on the first: importing a source is
    the owner's own deliberate act per source, same as that one.

    Idempotent: running this twice without a new dated comment in the
    file records nothing new the second time
    (`import_pra_tests_comments`'s own docstring).
    """

    summary = import_pra_tests_comments()

    print("Explications Import — pra_tests.yml dated comments")
    print(f"- Blocks seen: {summary.blocks_seen}")
    print(f"- Blocks skipped (no subject or date): {summary.blocks_skipped}")
    print(f"- Subjects seen: {summary.subjects_seen}")
    print(f"- Explications recorded: {summary.explications_recorded}")
    print(f"- Already imported (skipped): {summary.explications_already_imported}")


if __name__ == "__main__":
    main()
