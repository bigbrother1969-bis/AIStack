"""
The version is declared in one place and read from there.

`src/aistack/__main__.py` printed a literal `version 0.1.0` from
2026-07 until 2026-08-29, while `pyproject.toml` declared the same
number. **Two declarations of one fact, and nothing compared
them.** The literal was still correct, by luck: had anyone bumped
the distribution first, the command would have gone on announcing
the previous version to whoever asked it.

That is the shape FDN-P-005 names and this heritage keeps paying
for — a fact stated twice, right until the day the two are
edited apart. It is caught here rather than by reading, because
reading is what missed it for two months.
"""

from __future__ import annotations

import ast
import re
import subprocess
from pathlib import Path

import pytest

from aistack.__main__ import declared_version


ROOT = Path(__file__).parents[2]

VERSION = re.compile(r'^version\s*=\s*"([^"]+)"', re.M)


@pytest.fixture
def declared() -> str:
    """The version `pyproject.toml` declares — the single source."""

    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    found = VERSION.search(text)

    assert found, "pyproject.toml declares no version"

    return found.group(1)


def tracked_python_sources() -> list[Path]:
    """
    The repository's modules, not the working tree's.

    `git ls-files` rather than a walk: a stale build artifact or
    an untracked scratch file is not part of the heritage, and
    measuring the tree instead of the repository is the mistake
    GOV-0002/OS-001 recorded.
    """

    output = subprocess.check_output(
        ["git", "ls-files", "src/**/*.py"],
        cwd=ROOT,
        text=True,
    )

    return [ROOT / line for line in output.splitlines() if line]


def code_string_constants(source: str) -> list[str]:
    """
    Every string the module *evaluates*, docstrings excluded.

    **The first version of this test read the file as text**, and
    it failed on its own subject: the docstring of `__main__.py`
    explains the history by naming the version, and a historical
    sentence is not a second declaration — it is correct for ever.
    A prose mention going stale is not the defect; a value the
    program prints going stale is.

    So the reader is an `ast` walk with docstrings removed, which
    is the distinction the check has to make and could not make
    by grep.
    """

    tree = ast.parse(source)

    docstrings = {
        node.body[0].value
        for node in ast.walk(tree)
        if isinstance(
            node,
            (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef),
        )
        and node.body
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
        and isinstance(node.body[0].value.value, str)
    }

    return [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and node not in docstrings
    ]


def test_no_module_repeats_the_declared_version(declared):
    """
    The regression itself: a version literal the program
    evaluates is a second declaration.

    Mutation 2026-08-29: putting `print("version 0.2.0")` back
    into `__main__.py` turns this red, and moving the same text
    into a docstring does not — which is the line this test is
    drawn on.
    """

    offenders = [
        path.relative_to(ROOT).as_posix()
        for path in tracked_python_sources()
        if any(
            declared in value
            for value in code_string_constants(
                path.read_text(encoding="utf-8")
            )
        )
    ]

    assert offenders == [], (
        f"{declared} is declared by pyproject.toml and repeated in "
        f"{offenders}: read it with importlib.metadata instead"
    )


def test_an_uninstalled_tree_reports_unknown_rather_than_guessing():
    """
    `declared_version` reads installed distribution metadata,
    which a bare source tree does not have. **The absence is
    reported, not defaulted** — FDN-0003 Article 12 makes the
    absence of a fact a state rather than a reason to invent one.

    The value is not asserted, because it depends on whether this
    suite runs against an installed distribution. What is asserted
    is that both outcomes are strings and neither raises: a
    version command that crashes on an uninstalled checkout would
    be a worse answer than `unknown`.
    """

    reported = declared_version()

    assert type(reported) is str
    assert reported
