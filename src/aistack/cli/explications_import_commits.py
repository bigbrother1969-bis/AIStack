from __future__ import annotations

from aistack.explications import import_commits


def main() -> None:
    """
    Import this repository's own commit history as Explications
    (`ADR-0011` § *Decision* 8) — the fourth and last of the four real
    sources that ADR names, and the third of
    `aistack.cli.explications_import`'s own "siblings". A separate
    command, not a flag on the other three: importing a source is the
    owner's own deliberate act per source, same as those.

    Idempotent by commit sha: running this twice without a new commit
    matching the conventional `type(scope): message` shape records
    nothing new the second time (`import_commits`'s own docstring).

    A first run against this repository's full history takes a few
    minutes, not seconds — `import_commits`'s own docstring explains
    why (a real, measured write-pacing cost, not a stall).
    """

    summary = import_commits()

    print("Explications Import — commit history")
    print(f"- Commits seen: {summary.commits_seen}")
    print(f"- Commits skipped (no conventional scope): {summary.commits_skipped}")
    print(f"- Subjects seen: {summary.subjects_seen}")
    print(f"- Explications recorded: {summary.explications_recorded}")
    print(f"- Already imported (skipped): {summary.explications_already_imported}")


if __name__ == "__main__":
    main()
