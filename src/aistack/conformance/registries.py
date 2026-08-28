"""
Measure what the Kernel registers and what asks for it.

Two halves, taken two ways, because the questions are not the
same shape.

**What is registered** is read by composing the Kernel. The
bootstrap is the only authority on what a running AIStack holds,
and reading it any other way would be a second implementation of
`create_kernel()` that could disagree with the first.

**What retrieves** is read from the source, with `ast`. Running
the code would measure one execution — whichever CLI happened to
be invoked — where the question is about the repository. That
choice has a cost and it is stated in `RegistryInventory`: a
registry bound to a local name before being asked is invisible
here.

The repository, not the working tree: the file list comes from
`git ls-files`. `find` returned `src/aistack/funnel` for five
weeks after its files were removed (GOV-0002/OS-018), and a
measurement of a directory nobody tracks is a measurement of
somebody's disk.
"""

from __future__ import annotations

import ast
import dataclasses
import subprocess
from pathlib import Path

from aistack.contracts.registry_inventory import (
    RegisteredEntry,
    RegistryInventory,
    RetrievalSite,
)


RETRIEVAL = "get"

TESTS = "tests/"


def tracked_sources(root: Path) -> list[str] | None:
    """
    Every Python file the repository tracks, or `None`.

    `None` when git cannot answer — no repository, no git — and
    that is not an empty list. A measurement that quietly walked
    zero files would publish *nothing retrieves anything*.
    """

    try:
        listed = subprocess.check_output(
            ["git", "ls-files", "*.py"],
            cwd=root,
            text=True,
        )

    except Exception:
        return None

    return [line for line in listed.splitlines() if line]


def registry_names() -> tuple[str, ...]:
    """The attributes the Kernel Context carries."""

    from aistack.kernel.registries import KernelRegistries

    return tuple(
        field.name
        for field in dataclasses.fields(KernelRegistries)
    )


def registered_entries() -> tuple[RegisteredEntry, ...]:
    """
    What `create_kernel()` leaves in each registry.

    The bootstrap is composed, not read: it is the Composition
    Root, and asking it is the only way to answer without writing
    a second one.
    """

    from aistack.kernel.bootstrap import create_kernel

    kernel = create_kernel()

    found: list[RegisteredEntry] = []

    for name in registry_names():

        registry = getattr(kernel.registries, name)

        for identifier, entry in sorted(registry.all().items()):

            subject = type(entry) if not isinstance(entry, type) else entry

            found.append(
                RegisteredEntry(
                    registry=name,
                    identifier=identifier,
                    entry=(
                        f"{subject.__module__}.{subject.__qualname__}"
                    ),
                )
            )

    return tuple(found)


def retrieval_sites(
    source: str,
    path: str,
    registries: tuple[str, ...],
) -> list[RetrievalSite]:
    """
    Every `<something>.<registry>.get(...)` in one file.

    Matched on the attribute name rather than on the expression
    before it, so `self.tasks.get(...)` counts: `TaskResolver`
    receives `kernel.registries.tasks` and stores it, which is the
    ordinary way a component holds a registry and would be missed
    by a rule that required the full path.

    The cost of that rule is an attribute merely sharing a
    registry's name, counted here as a retrieval. It is declared
    rather than guarded against: a guard would need to resolve
    names, which is the type checker's job and not this one's.
    """

    tree = ast.parse(source, filename=path)

    found: list[RetrievalSite] = []

    for node in ast.walk(tree):

        if not isinstance(node, ast.Call):
            continue

        callee = node.func

        if not isinstance(callee, ast.Attribute):
            continue

        if callee.attr != RETRIEVAL:
            continue

        receiver = callee.value

        if not isinstance(receiver, ast.Attribute):
            continue

        if receiver.attr not in registries:
            continue

        identifier = None

        if node.args:
            first = node.args[0]
            if isinstance(first, ast.Constant) and isinstance(
                first.value, str
            ):
                identifier = first.value

        found.append(
            RetrievalSite(
                registry=receiver.attr,
                identifier=identifier,
                site=f"{path}:{callee.lineno}",
                in_tests=path.startswith(TESTS),
            )
        )

    return found


def take_registry_inventory(root: Path) -> RegistryInventory:
    """
    Compose the Kernel, then read the repository that asks it.

    Returns an unmeasured inventory rather than a partial one when
    git cannot list the sources: the registrations alone would
    make every capability look unretrieved.
    """

    registries = registry_names()

    tracked = tracked_sources(root)

    if tracked is None:
        return RegistryInventory(registries=registries)

    retrievals: list[RetrievalSite] = []
    unreadable: list[tuple[str, str]] = []

    for relative in tracked:

        path = root / relative

        try:
            retrievals.extend(
                retrieval_sites(
                    path.read_text(encoding="utf-8"),
                    relative,
                    registries,
                )
            )

        except Exception as error:
            # Deliberately broad, and named in the result. A file
            # that will not parse is a fact about the repository;
            # a measurement that stopped at the first one would
            # measure nothing at all.
            unreadable.append(
                (relative, f"{type(error).__name__}: {error}")
            )

    return RegistryInventory(
        registries=registries,
        registered=registered_entries(),
        retrievals=tuple(
            sorted(
                retrievals,
                key=lambda r: (r.registry, r.site),
            )
        ),
        sources=len(tracked),
        unreadable=tuple(unreadable),
        measured=True,
    )
