#!/usr/bin/env python3
"""Measure how far the source tree is from the GHE principles.

Read-only, standard library only. It parses `src/aistack` and reports,
for the C3 principles a program can measure, every place that departs
from them:

    python scripts/ghe_audit.py            the report, as Markdown
    python scripts/ghe_audit.py --json     the measures, as JSON

`tests/unit/scripts/test_ghe_audit.py` compares the measures with
`tests/reference/ghe_audit_baseline.json`: a departure that is not in
the baseline fails the suite, and so does a baseline entry that no
longer exists. The list can only get shorter.

The principles are cited by their identifier in the registry
(`FDN-0012`, kept at the tag `archive/heritage-2.0.0-rc1`).
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "aistack"

# Calls that change something on disk.
WRITING_METHODS = {"write_text", "write_bytes", "unlink", "rmdir", "touch"}
# `Path.replace` and `Path.rename` take one argument; `str.replace` takes two.
MOVING_METHODS = {"replace", "rename"}
WRITING_FUNCTIONS = {
    "os.replace",
    "os.rename",
    "os.remove",
    "os.unlink",
    "shutil.move",
    "shutil.copy",
    "shutil.copy2",
    "shutil.copyfile",
    "shutil.copytree",
    "shutil.rmtree",
}

def _source_root(root: Path) -> Path:
    return root / "src" / PACKAGE


def _modules(root: Path) -> list[Path]:
    return sorted(
        path for path in _source_root(root).rglob("*.py") if "__pycache__" not in path.parts
    )


def _relative(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _module_name(root: Path, path: Path) -> str:
    parts = list(path.relative_to(root / "src").with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _imports(root: Path, path: Path, tree: ast.AST) -> set[str]:
    """Every `aistack.*` module named by an import of this file."""

    here = _module_name(root, path).split(".")
    if path.name != "__init__.py":
        here = here[:-1]
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = here[: len(here) - node.level + 1]
                name = ".".join(base + ([node.module] if node.module else []))
            else:
                name = node.module or ""
            found.add(name)
    return {name for name in found if name == PACKAGE or name.startswith(PACKAGE + ".")}


def _area(module: str) -> str:
    """`aistack.providers.docker.x` -> `providers`."""

    parts = module.split(".")
    return parts[1] if len(parts) > 1 else ""


def _dotted(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_dotted(node.value)}.{node.attr}"
    return ""


def _opens_for_writing(call: ast.Call) -> bool:
    mode: ast.AST | None = call.args[1] if len(call.args) > 1 else None
    if isinstance(call.func, ast.Attribute) and call.func.attr == "open":
        mode = call.args[0] if call.args else None
    for keyword in call.keywords:
        if keyword.arg == "mode":
            mode = keyword.value
    return (
        isinstance(mode, ast.Constant)
        and isinstance(mode.value, str)
        and any(letter in mode.value for letter in "wax+")
    )


def _writes(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _dotted(node.func)
        if name in WRITING_FUNCTIONS:
            return True
        if name == "open" or name.endswith(".open"):
            if _opens_for_writing(node):
                return True
            continue
        if isinstance(node.func, ast.Attribute):
            method = node.func.attr
            if method in WRITING_METHODS:
                return True
            if method in MOVING_METHODS and len(node.args) == 1 and not node.keywords:
                return True
    return False


def measure(root: Path = ROOT) -> dict[str, list[str]]:
    """The departures, one sorted list of strings per measure."""

    trees = {path: ast.parse(path.read_text(encoding="utf-8")) for path in _modules(root)}
    imports = {path: _imports(root, path, tree) for path, tree in trees.items()}
    source = _source_root(root)

    def inside(path: Path, *parts: str) -> bool:
        return path.is_relative_to(source.joinpath(*parts))

    # ARC-P-004 - technology-specific concepts never belong in the Kernel.
    # ARC-P-001 - the Kernel is generic: it depends on nothing outside itself.
    # The composition root (`kernel/bootstrap`) is where the outside is
    # allowed to be named, except for a technology.
    kernel_imports = sorted(
        f"{_relative(root, path)} -> {name}"
        for path, names in imports.items()
        if inside(path, "kernel")
        for name in names
        if _area(name) not in ("kernel", "")
        and (not inside(path, "kernel", "bootstrap") or _area(name) in ("providers", "generators"))
    )

    # ARC-P-002 - what runs is registered at bootstrap and reached through
    # the Kernel. An entry point that never builds the Kernel bypasses it.
    entry_points = [path for path in trees if inside(path, "cli") and path.name != "__init__.py"]
    entry_points.append(source / "web" / "app.py")
    bypassing = sorted(
        _relative(root, path)
        for path in entry_points
        if path in trees and not any(name.startswith(f"{PACKAGE}.kernel") for name in imports[path])
    )

    # ARC-P-002 - a Task is registered to be executed. Nothing outside the
    # Kernel reaching the execution machinery means it is registered only.
    machinery = (f"{PACKAGE}.kernel.execution", f"{PACKAGE}.kernel.resolution", f"{PACKAGE}.kernel.tasks")
    task_callers = sorted(
        _relative(root, path)
        for path, names in imports.items()
        if not inside(path, "kernel") and any(name.startswith(machinery) for name in names)
    )
    unexecuted = [] if task_callers else ["no module outside the Kernel executes a registered Task"]

    # GOV-P-002 - every modification is a governed transaction.
    # ARC-P-012 - providers observe and collect; they never modify.
    # Writing a generated artifact is legitimate (ENG-P-003); telling it
    # from a modification of knowledge is a reading, done in lot 6. What
    # is measured is where the disk is written outside `transaction`.
    writers = sorted(
        _relative(root, path)
        for path, tree in trees.items()
        if not inside(path, "transaction") and _writes(tree)
    )

    # FDN-P-005, FDN-P-006 - the principles have one governed place, and
    # it is read where the work is done.
    registry = root / "docs" / "00-foundation" / "FDN-0012-AIStack-Principles-Registry.md"
    missing = [] if registry.is_file() else [_relative(root, registry)]

    return {
        "kernel_depends_on_the_outside": kernel_imports,
        "entry_points_bypassing_the_kernel": bypassing,
        "registered_tasks_never_executed": unexecuted,
        "disk_writes_outside_a_transaction": writers,
        "principles_missing_from_the_tree": missing,
    }


TITLES = {
    "kernel_depends_on_the_outside": (
        "ARC-P-001, ARC-P-004",
        "The Kernel names something outside itself",
    ),
    "entry_points_bypassing_the_kernel": (
        "ARC-P-002",
        "An entry point never builds the Kernel",
    ),
    "registered_tasks_never_executed": (
        "ARC-P-002",
        "A registered Task is never executed",
    ),
    "disk_writes_outside_a_transaction": (
        "GOV-P-002, ARC-P-012",
        "The disk is written outside a transaction",
    ),
    "principles_missing_from_the_tree": (
        "FDN-P-005, FDN-P-006",
        "The principles registry is not in the tree",
    ),
}


def report(measures: dict[str, list[str]]) -> str:
    lines = ["# GHE audit", "", "| Principles | Departure | Count |", "|---|---|---|"]
    for key, (principles, title) in TITLES.items():
        lines.append(f"| {principles} | {title} | {len(measures[key])} |")
    for key, (principles, title) in TITLES.items():
        lines += ["", f"## {title} ({principles})", ""]
        lines += [f"- `{entry}`" for entry in measures[key]] or ["None."]
    return "\n".join(lines) + "\n"


def main(arguments: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", action="store_true", help="print the measures as JSON")
    options = parser.parse_args(arguments)
    measures = measure()
    if options.json:
        print(json.dumps(measures, indent=2, ensure_ascii=False))
    else:
        print(report(measures), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
