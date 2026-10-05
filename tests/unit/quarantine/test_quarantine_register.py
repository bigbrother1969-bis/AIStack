from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from aistack.quarantine.register import (
    QuarantineEntry,
    entry_of_module,
    entry_of_path,
    load_register,
)


def _entry(**changes: object) -> QuarantineEntry:
    values: dict[str, object] = {
        "id": "Q-900",
        "paths": ("src/aistack/old/", "tools/run.py", "scripts/old.sh"),
        "reason": "unused",
        "since": date(2026, 10, 5),
        "review_after": date(2026, 11, 16),
    }
    values.update(changes)
    return QuarantineEntry(**values)  # type: ignore[arg-type]


def test_modules_are_read_from_the_python_paths() -> None:
    assert _entry(paths=("src/aistack/old/__init__.py", "tools/run.py", "scripts/old.sh")).modules() == (
        "aistack.old",
        "tools.run",
    )


def test_a_directory_holds_what_is_under_it() -> None:
    entry = _entry()
    assert entry.holds("src/aistack/old/a.py")
    assert entry.holds("scripts/old.sh")
    assert not entry.holds("src/aistack/older/a.py")
    assert not entry.holds("scripts/old.sh.bak")


@pytest.mark.parametrize(
    "changes",
    [
        {"id": " "},
        {"paths": ()},
        {"paths": ("/etc/passwd",)},
        {"paths": ("../outside",)},
        {"reason": ""},
        {"review_after": date(2026, 10, 5)},
    ],
)
def test_an_entry_that_says_too_little_is_refused(changes: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        _entry(**changes)


def test_the_register_is_read(tmp_path: Path) -> None:
    register = tmp_path / "register.yml"
    register.write_text(
        "entries:\n"
        "  - id: Q-1\n    paths: [src/aistack/item/]\n    reason: >\n      dead\n      code\n"
        "    since: 2026-10-05\n    review_after: 2026-11-16\n    amend: [README.md]\n",
        encoding="utf-8",
    )
    (entry,) = load_register(register)
    assert entry.reason == "dead code"
    assert entry.amend == ("README.md",)
    assert entry.modules() == ("aistack.item",)


def test_an_identifier_used_twice_is_refused(tmp_path: Path) -> None:
    register = tmp_path / "register.yml"
    item = "  - {id: Q-1, paths: [a.sh], reason: x, since: 2026-10-05, review_after: 2026-11-16}\n"
    register.write_text("entries:\n" + item + item, encoding="utf-8")
    with pytest.raises(ValueError):
        load_register(register)


def test_a_use_finds_its_entry() -> None:
    entries = (_entry(paths=("src/aistack/old/__init__.py", "scripts/old.sh")),)
    assert entry_of_module(entries, "aistack.old.deep") is entries[0]
    assert entry_of_module(entries, "aistack.older") is None
    assert entry_of_path(entries, "scripts/old.sh") is entries[0]


def test_the_shipped_register_is_six_weeks_from_the_owner_s_decision() -> None:
    entries = load_register()
    assert {entry.since for entry in entries} == {date(2026, 10, 5)}
    assert {entry.review_after for entry in entries} == {date(2026, 11, 16)}
