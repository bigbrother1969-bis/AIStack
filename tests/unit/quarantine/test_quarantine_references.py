"""
The quarantine's guard (`OPS-0012`): nothing outside the quarantine
starts depending on what is in it, every quarantined file is still
there, and every quarantined program carries its tripwire.

Run by the suite on the laptop and on GIGABYTE before every push, so a
new reference to quarantined code fails before it is published.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

from aistack.quarantine.register import GENERIC_NAMES, REGISTER, load_register

ROOT = Path(__file__).resolve().parents[3]

# Files that may name quarantined ones without depending on them: the
# register and its policy, the frozen heritage, generated reports and
# the release notes, which record history.
ALWAYS_ALLOWED = (
    "src/aistack/quarantine/",
    "tests/unit/quarantine/",
    "docs/04-development/OPS-0012-Dead-Code-Quarantine.md",
    "docs/03-handbook/RELEASE-NOTES.md",
    "scripts/quarantine_tripwire.sh",
    "archive/",
    "reports/generated/",
)


def _tracked() -> list[str]:
    try:
        result = subprocess.run(
            ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
        )
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("not a git checkout")
    return result.stdout.splitlines()


def _patterns(paths: tuple[str, ...], modules: tuple[str, ...], files: list[str]) -> list[re.Pattern[str]]:
    texts = set(paths)
    for module in modules:
        if "." in module:
            texts.add(module)
    for path in paths:
        held = [name for name in files if name == path or (path.endswith("/") and name.startswith(path))]
        for name in held:
            base = Path(name).name
            if base not in GENERIC_NAMES and not base.endswith(".py"):
                texts.add(base)
    return [
        re.compile(r"(?<![\w./-])" + re.escape(text) + r"(?![\w-])")
        for text in sorted(texts)
    ]


def test_the_register_reads() -> None:
    assert load_register(REGISTER)


def test_every_quarantined_path_is_still_there() -> None:
    files = _tracked()
    for entry in load_register(REGISTER):
        for path in entry.paths:
            assert any(name == path or (path.endswith("/") and name.startswith(path)) for name in files), (
                f"{entry.id}: {path} is no longer tracked — remove it from the register "
                f"(OPS-0012: an item leaves the register when it is deleted)"
            )


def test_nothing_outside_the_quarantine_refers_to_it() -> None:
    files = _tracked()
    entries = load_register(REGISTER)
    offenders = []
    for entry in entries:
        patterns = _patterns(entry.paths, entry.modules(), files)
        for name in files:
            if name.startswith(ALWAYS_ALLOWED) or name in entry.amend:
                continue
            if any(other.holds(name) for other in entries):
                continue
            try:
                text = (ROOT / name).read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            for pattern in patterns:
                if pattern.search(text):
                    offenders.append(f"{name} names {pattern.pattern} ({entry.id})")
    assert not offenders, (
        "files outside the quarantine refer to quarantined code — take the "
        "item out of the register, or list the file in its `amend`:\n"
        + "\n".join(offenders)
    )


def test_every_quarantined_program_carries_its_tripwire() -> None:
    files = _tracked()
    missing = []
    for entry in load_register(REGISTER):
        for name in files:
            if not entry.holds(name) or name.startswith("tests/"):
                continue
            text = (ROOT / name).read_text(encoding="utf-8")
            if name.endswith(".py") and "tripwire(__name__)" not in text:
                missing.append(name)
            if name.endswith(".sh") and f"quarantine_tripwire {name}" not in text:
                missing.append(name)
    assert not missing, f"quarantined without a tripwire: {missing}"


def test_a_planted_reference_is_found() -> None:
    patterns = _patterns(("tools/", "src/aistack/item/"), ("aistack.item",), ["tools/run.sh"])
    def found(text: str) -> bool:
        return any(pattern.search(text) for pattern in patterns)

    assert found("from aistack.item.models import Item")
    assert found("see tools/ for the runner")
    assert found("run.sh does it")
    assert not found("devtools/ and other tools")
    assert not found("aistack.items is something else")
