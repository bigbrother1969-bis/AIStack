#!/usr/bin/env python3
"""Measure how far the source tree is from the GHE principles.

Read-only, standard library only. It parses `src/aistack` and reports,
for the principles a program can measure, every place that departs
from them, and every citation that leads nowhere:

    python scripts/ghe_audit.py            the report, as Markdown
    python scripts/ghe_audit.py --json     the measures, as JSON

`tests/unit/scripts/test_ghe_audit.py` compares the measures with
`tests/reference/ghe_audit_baseline.json`: a departure that is not in
the baseline fails the suite, and so does a baseline entry that no
longer exists. The list can only get shorter.

The principles are cited by their identifier in the registry
(`docs/00-foundation/FDN-0012-AIStack-Principles-Registry.md`).
"""

from __future__ import annotations

import argparse
import ast
import json
import re
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

# A governed document (`FDN-0012`) and a principle (`FDN-P-005`).
DOCUMENT = re.compile(r"\b(?:FDN|ARCH|ADR|STD|GOV|OPS|ENG-TEST|CMP|QUAL)-\d{4}\b")
PRINCIPLE = re.compile(r"\b[A-Z]{2,5}-P-\d{3}\b")
REGISTRY = "docs/00-foundation/FDN-0012-AIStack-Principles-Registry.md"
INDEX = "docs/00-foundation/FDN-0001-README.md"
KEPT_AT_THE_TAG = "## Kept at the tag"
# The generic mechanisms the Kernel may name (`ADR-0027` § 7): they carry
# no technology. Everything else outside the Kernel is one, or leads to one.
GENERIC = (
    "aistack.transport",
    "aistack.transaction",
    "aistack.history",
    "aistack.generators.history",
)
# What is written outside a transaction on purpose. `ADR-0027` § 11 reads
# each of these files and the owner declared them exempt on 2026-11-17: what
# they write is not a person's knowledge, and no person's choice triggers it.
# A file is added here only by a decision recorded in that ADR; the audit
# lists them apart so that what is left to do reads on its own.
STATE = "the state a service keeps for itself"
LOCK = "a process lock"
INSTALLATION = "the installation"
MAINTENANCE = "the maintenance"
PROJECTION = "the projection, generated whole and never edited"
EXEMPT_WRITES = {
    "src/aistack/api_keys/__init__.py": "the API keys: no secret in a payload or a trace",
    "src/aistack/arrivals/state.py": STATE,
    "src/aistack/cli/config_init.py": INSTALLATION,
    "src/aistack/cli/docker_diff_monitor.py": STATE,
    "src/aistack/cli/docker_digest_monitor.py": STATE,
    "src/aistack/cli/docker_events_monitor.py": STATE,
    "src/aistack/cli/docker_packages_monitor.py": STATE,
    "src/aistack/cli/sync_apply.py": LOCK,
    "src/aistack/data_budget/budget.py": MAINTENANCE,
    "src/aistack/context_bundle/export/bundle_exporter.py": PROJECTION,
    "src/aistack/context_bundle/export/markdown_bundle_exporter.py": PROJECTION,
    "src/aistack/context_bundle/export/zip_bundle_exporter.py": PROJECTION,
    "src/aistack/dock/executor.py": LOCK,
    "src/aistack/dock/proposals.py": STATE,
    "src/aistack/explications/human.py": MAINTENANCE,
    "src/aistack/generators/filesystem/yaml/store.py": STATE,
    "src/aistack/generators/history.py": "the recognised writer of generated artifacts",
    "src/aistack/host_collector.py": STATE,
    "src/aistack/instance/declarations.py": INSTALLATION,
    "src/aistack/instance/first_start.py": INSTALLATION,
    "src/aistack/instance/setup_wizard.py": INSTALLATION,
    "src/aistack/pra/scheduled.py": STATE,
    "src/aistack/providers/docker/digest_history.py": STATE,
    "src/aistack/restart_watch/guard.py": STATE,
    "src/aistack/restart_watch/journal.py": STATE,
    "src/aistack/sandbox/run.py": STATE,
    "src/aistack/sync/screen.py": STATE,
    "src/aistack/vigil/notify.py": STATE,
    "src/aistack/vigil/snapshot.py": STATE,
}
# The audit's own test names identifiers that exist only in its fixtures.
OWN_TEST = "tests/unit/scripts/test_ghe_audit.py"
# So do the tests of the integrity checks: a check that reads identifiers in
# a bundle is tested on identifiers invented for the case (a decision numbered zero, an
# unregistered principle), which is what the check has to recognise.
FIXTURE_TESTS = "tests/unit/integrity"
READ = ("src", "tests", "docs", "scripts", "README.md")
TEXT = {".py", ".md", ".yml", ".yaml", ".sh", ".toml", ".html", ".txt", ".cfg"}


def _texts(root: Path) -> dict[Path, str]:
    """The text of everything a contributor reads or runs."""

    found: dict[Path, str] = {}
    for name in READ:
        start = root / name
        paths = [start] if start.is_file() else sorted(start.rglob("*")) if start.is_dir() else []
        for path in paths:
            if path == root / OWN_TEST or path.is_relative_to(root / FIXTURE_TESTS):
                continue
            if path.is_file() and path.suffix in TEXT and "__pycache__" not in path.parts:
                found[path] = path.read_text(encoding="utf-8", errors="replace")
    return found


def _registered_tasks(root: Path) -> list[tuple[str, str]]:
    """The Tasks `registrations.yml` declares, as (identifier, class name).

    Read without a YAML library: the file is a list of `- id:` entries,
    each followed by its `factory: module:Class`.
    """

    declaration = root / "src" / PACKAGE / "registrations.yml"
    if not declaration.is_file():
        return []
    _, found, section = ("\n" + declaration.read_text(encoding="utf-8")).partition("\ntasks:\n")
    if not found:
        return []
    tasks: list[tuple[str, str]] = []
    identifier = ""
    for line in section.splitlines():
        if line and not line.startswith((" ", "#")):
            break
        entry = line.strip()
        if entry.startswith("- id:"):
            identifier = entry.removeprefix("- id:").strip()
        elif entry.startswith("factory:") and identifier:
            tasks.append((identifier, entry.removeprefix("factory:").strip().rpartition(":")[2]))
            identifier = ""
    return tasks


def _registered(root: Path) -> set[str]:
    """The principles the registry declares: the first cell of a table row."""

    registry = root / REGISTRY
    if not registry.is_file():
        return set()
    rows = (line.split("|") for line in registry.read_text(encoding="utf-8").splitlines())
    return {row[1].strip() for row in rows if len(row) > 2 and PRINCIPLE.fullmatch(row[1].strip())}


def _kept_at_the_tag(root: Path) -> set[str]:
    """The documents the Foundation index declares kept at the tag."""

    index = root / INDEX
    if not index.is_file():
        return set()
    _, found, section = index.read_text(encoding="utf-8").partition(KEPT_AT_THE_TAG)
    section = section.split("\n## ", 1)[0] if found else ""
    cells = (line.split("|")[1].strip() for line in section.splitlines() if line.startswith("|"))
    return {cell for cell in cells if DOCUMENT.fullmatch(cell)}


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

    # ARC-P-001, ARC-P-004 - the Kernel is generic: it names no technology.
    # It may name a generic mechanism, and the list of those is declared
    # above. Its bootstrap is held to the same rule as the rest of it.
    def generic(name: str) -> bool:
        return any(name == module or name.startswith(module + ".") for module in GENERIC)

    kernel_imports = sorted(
        f"{_relative(root, path)} -> {name}"
        for path, names in imports.items()
        if inside(path, "kernel")
        for name in names
        if _area(name) not in ("kernel", "") and not generic(name)
    )

    # ARC-P-002 - what runs is registered at bootstrap and reached through
    # the Kernel. An entry point that never builds the Kernel bypasses it.
    entry_points = [path for path in trees if inside(path, "cli") and path.name != "__init__.py"]
    entry_points.append(source / "web" / "app.py")
    builds_the_kernel = [
        path
        for path in entry_points
        if path in trees and any(name.startswith(f"{PACKAGE}.kernel") for name in imports[path])
    ]
    bypassing = sorted(
        _relative(root, path) for path in entry_points if path in trees and path not in builds_the_kernel
    )

    # ARC-P-002 - an entry point that builds the Kernel for its providers
    # and never executes through the Runtime runs a chain the Runtime does
    # not trace.
    runtime = f"{PACKAGE}.kernel.runtime"
    outside_the_runtime = sorted(
        _relative(root, path)
        for path in builds_the_kernel
        if not any(name == runtime or name.startswith(runtime + ".") for name in imports[path])
    )

    # ARC-P-002 - a Task is registered to be executed. A module outside
    # the Kernel and `aistack/tasks` executes one when it names it and
    # hands a Request to the Runtime, resolves the Task itself, or asks
    # the registry for it. Declaring a Task is not executing it. Each
    # registered Task is held to this, not the registry as a whole: one
    # Task nobody executes would otherwise hide behind another.
    executing = (f"{PACKAGE}.kernel.runtime", f"{PACKAGE}.kernel.resolution")
    callers = {
        path: path.read_text(encoding="utf-8")
        for path, names in imports.items()
        if not inside(path, "kernel")
        and not inside(path, "tasks")
        and (
            any(name == module or name.startswith(module + ".") for name in names for module in executing)
            or ".registries.tasks" in path.read_text(encoding="utf-8")
        )
    }
    unexecuted = sorted(
        f"{identifier} ({class_name})"
        for identifier, class_name in _registered_tasks(root)
        if not any(
            class_name in text or f"\"{identifier}\"" in text or f"'{identifier}'" in text
            for text in callers.values()
        )
    )

    # ARC-P-002 - application code asks the Kernel for a provider; it does
    # not build one (`FDN-0004`, Kernel Bootstrap Principle). A provider is
    # a class of `aistack/providers` whose name ends in `Provider`.
    providers = {
        node.name
        for path, tree in trees.items()
        if inside(path, "providers")
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef) and node.name.endswith("Provider")
    }
    built = sorted(
        {
            f"{_relative(root, path)} -> {name}"
            for path, tree in trees.items()
            if not inside(path, "providers") and not inside(path, "kernel")
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and (name := _dotted(node.func).rpartition(".")[2]) in providers
        }
    )

    # GOV-P-002 - every modification is a governed transaction.
    # ARC-P-012 - providers observe and collect; they never modify.
    # Writing a generated artifact is legitimate (ENG-P-003); telling it
    # from a modification of knowledge is a reading, done in lot 6. What
    # is measured is where the disk is written outside `transaction`.
    # Declared exempt (`ADR-0027` § 11) is listed apart: what is left to do
    # is what remains.
    writing = sorted(
        _relative(root, path)
        for path, tree in trees.items()
        if not inside(path, "transaction") and _writes(tree)
    )
    writers = [name for name in writing if name not in EXEMPT_WRITES]
    exempt = [f"{name} ({EXEMPT_WRITES[name]})" for name in writing if name in EXEMPT_WRITES]

    # FDN-P-005, FDN-P-006 - the principles have one governed place, and
    # it is read where the work is done.
    registry = root / REGISTRY
    missing = [] if registry.is_file() else [REGISTRY]

    # FDN-P-005 - a cited document, or a cited principle, exists. What is
    # cited and is not in the tree cannot be read by who follows the
    # citation, unless the Foundation index says it is kept at the tag.
    texts = _texts(root)
    documents = root / "docs"
    present = {
        match.group()
        for path in texts
        if path.is_relative_to(documents) and (match := DOCUMENT.match(path.name))
    }
    cited_documents = {name for text in texts.values() for name in DOCUMENT.findall(text)}
    cited_principles = {name for text in texts.values() for name in PRINCIPLE.findall(text)}
    registered = _registered(root)

    return {
        "kernel_names_what_is_not_generic": kernel_imports,
        "entry_points_bypassing_the_kernel": bypassing,
        "entry_points_outside_the_runtime": outside_the_runtime,
        "registered_tasks_never_executed": unexecuted,
        "providers_built_by_application_code": built,
        "disk_writes_outside_a_transaction": writers,
        "disk_writes_declared_exempt": exempt,
        "principles_missing_from_the_tree": missing,
        "documents_cited_and_absent": sorted(cited_documents - present - _kept_at_the_tag(root)),
        "principles_cited_and_not_registered": sorted(cited_principles - registered) if registered else [],
    }


TITLES = {
    "kernel_names_what_is_not_generic": (
        "ARC-P-001, ARC-P-004",
        "The Kernel names something that is not a generic mechanism",
    ),
    "entry_points_bypassing_the_kernel": (
        "ARC-P-002",
        "An entry point never builds the Kernel",
    ),
    "entry_points_outside_the_runtime": (
        "ARC-P-002",
        "An entry point builds the Kernel and never executes through the Runtime",
    ),
    "registered_tasks_never_executed": (
        "ARC-P-002",
        "A registered Task is never executed",
    ),
    "providers_built_by_application_code": (
        "ARC-P-002",
        "Application code builds a provider instead of asking the Kernel for it",
    ),
    "disk_writes_outside_a_transaction": (
        "GOV-P-002, ARC-P-012",
        "The disk is written outside a transaction",
    ),
    "disk_writes_declared_exempt": (
        "GOV-P-002",
        "The disk is written outside a transaction and the owner declared it exempt (ADR-0027 § 11)",
    ),
    "principles_missing_from_the_tree": (
        "FDN-P-005, FDN-P-006",
        "The principles registry is not in the tree",
    ),
    "documents_cited_and_absent": (
        "FDN-P-005",
        "A document is cited, is not in the tree and is not declared kept at the tag",
    ),
    "principles_cited_and_not_registered": (
        "FDN-P-005",
        "A principle is cited and the registry does not declare it",
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
