"""
GOV-0002/OS-011: an image carries only what the heritage knows about.

`aistack-core:0.1.0` was built on 2026-08-19 under a `.dockerignore`
whose `__pycache__` and `*.pyc` patterns matched **only the context
root**, so every `src/aistack/**/__pycache__` entered the image.
The owner deleted it from DockerHub on 2026-08-23 rather than
rebuilding.

`selection-ui:0.4` shipped the same residue with a sharper
consequence: two stale bytecode directories for façade modules
deleted that morning, whose `__init__.py` was gone while the
directory survived — so `import aistack.selection.engine` returned
an **empty namespace package instead of failing**.

Both conditions were repaired in `.dockerignore` and `Dockerfile`
on 2026-08-21 and 2026-08-22, and **neither was watched by
anything** until OPS-0002 v1.9 made image publication a governed
act on 2026-08-29. This file is that watch.

*What it cannot do is stated in OPS-0002 § *Publishing an image*:
no test verifies a published image. The suite has no registry, and
a check receives a projection rather than a network. What is
guarded is the state a build starts from.*
"""

from __future__ import annotations

from pathlib import Path

import pytest


ROOT = Path(__file__).parents[2]


@pytest.fixture
def dockerignore() -> list[str]:
    text = (ROOT / ".dockerignore").read_text(encoding="utf-8")

    return [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


@pytest.fixture
def dockerfile() -> str:
    return (ROOT / "Dockerfile").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "pattern",
    ["**/__pycache__", "**/*.pyc", "**/*.egg-info"],
)
def test_bytecode_is_excluded_anywhere_and_not_only_at_the_root(
    dockerignore, pattern
):
    """
    **`**/` is what makes a pattern mean *anywhere*.**

    A `.dockerignore` pattern is matched against a file's full
    path in the build context, not against its name — which is
    why `__pycache__` alone excluded `./__pycache__` and nothing
    below it. That single missing prefix is the whole of OS-011.

    Mutation 2026-08-29: dropping `**/` from any of these turns
    this red.
    """

    assert pattern in dockerignore, (
        f"{pattern!r} is missing from .dockerignore: without the `**/` "
        f"prefix the pattern matches only the context root, which is "
        f"the defect GOV-0002/OS-011 records"
    )


def test_the_build_writes_no_bytecode_in_the_first_place(dockerfile):
    """
    The second guard, and it is not a duplicate of the first.

    `.dockerignore` keeps the **host's** bytecode out of the
    context; `PYTHONDONTWRITEBYTECODE` keeps the **build** from
    producing its own. An image built from a clean context by an
    interpreter that caches would carry bytecode nobody excluded,
    and no `.dockerignore` pattern can reach it.
    """

    assert "PYTHONDONTWRITEBYTECODE=1" in dockerfile


def test_the_image_installs_the_distribution_rather_than_copying_a_tree(
    dockerfile,
):
    """
    `pip install .` is what makes `importlib.metadata` able to
    answer, which is what `aistack.__main__` now reads its version
    from. An image that copied `src/` onto the path would report
    `unknown` — correctly, and uselessly.

    Stated as a test because the two facts live in different files
    and nothing else relates them.
    """

    assert "pip install --no-cache-dir ." in dockerfile
    assert "COPY pyproject.toml" in dockerfile
