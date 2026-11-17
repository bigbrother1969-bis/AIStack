"""scripts/ghe_audit.py: the departures from the GHE principles are
measured, and the list can only get shorter."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[3]
BASELINE = ROOT / "tests" / "reference" / "ghe_audit_baseline.json"


def _audit() -> ModuleType:
    spec = importlib.util.spec_from_file_location("ghe_audit", ROOT / "scripts" / "ghe_audit.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _tree(tmp_path: Path, files: dict[str, str]) -> Path:
    for name, content in files.items():
        path = tmp_path / "src" / "aistack" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return tmp_path


def test_no_departure_is_added_and_none_is_kept_once_gone() -> None:
    measured = _audit().measure(ROOT)
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))

    assert measured.keys() == baseline.keys()
    for key in baseline:
        added = sorted(set(measured[key]) - set(baseline[key]))
        gone = sorted(set(baseline[key]) - set(measured[key]))
        assert not added, (
            f"{key}: a new departure from the GHE principles: {added}. "
            "Bring the change back within the principle; the baseline is not extended."
        )
        assert not gone, (
            f"{key}: no longer a departure: {gone}. "
            f"Remove it from {BASELINE.relative_to(ROOT)} so that it cannot come back."
        )


def test_the_kernel_naming_a_technology_is_a_departure(tmp_path: Path) -> None:
    root = _tree(
        tmp_path,
        {
            "kernel/core.py": "from aistack.kernel.registry import x\n",
            "kernel/tasks/discover.py": "from aistack.providers.docker import DockerProvider\n",
            "kernel/bootstrap/default.py": (
                "from aistack.transport import engine\nfrom aistack.catalog.views.music import MusicView\n"
            ),
            "kernel/tracing/file.py": (
                "from aistack.generators.history import write\nfrom aistack.generators.docker import Generator\n"
            ),
            "kernel/time/sequence.py": "from aistack.history.query import instants\n",
            "kernel/services/core.py": "from aistack.transaction.registry import Registry\n",
        },
    )

    assert _audit().measure(root)["kernel_names_what_is_not_generic"] == [
        "src/aistack/kernel/bootstrap/default.py -> aistack.catalog.views.music",
        "src/aistack/kernel/tasks/discover.py -> aistack.providers.docker",
        "src/aistack/kernel/tracing/file.py -> aistack.generators.docker",
    ]


def test_a_relative_import_is_resolved(tmp_path: Path) -> None:
    root = _tree(tmp_path, {"kernel/tasks/discover.py": "from ...generators import docker\n"})

    assert _audit().measure(root)["kernel_names_what_is_not_generic"] == [
        "src/aistack/kernel/tasks/discover.py -> aistack.generators"
    ]


def test_an_entry_point_that_never_builds_the_kernel_is_a_departure(tmp_path: Path) -> None:
    root = _tree(
        tmp_path,
        {
            "cli/__init__.py": "",
            "cli/through.py": "from aistack.kernel.bootstrap import create_kernel\n",
            "cli/around.py": "from aistack.health import score\n",
            "web/app.py": "from aistack.kernel.bootstrap import create_kernel\n",
        },
    )

    assert _audit().measure(root)["entry_points_bypassing_the_kernel"] == ["src/aistack/cli/around.py"]


def test_a_task_executed_from_outside_the_kernel_is_not_a_departure(tmp_path: Path) -> None:
    audit = _audit()
    declared = "from aistack.kernel.execution import Observation, Request\n"

    registered_only = _tree(tmp_path / "a", {"tasks/discover.py": declared, "cli/run.py": ""})
    resolved = _tree(
        tmp_path / "b",
        {"tasks/discover.py": declared, "cli/run.py": "from aistack.kernel.resolution import TaskResolver\n"},
    )
    asked_for = _tree(
        tmp_path / "c",
        {"cli/run.py": "def run(kernel):\n    return kernel.registries.tasks.get('x').execute(None)\n"},
    )
    through_the_runtime = _tree(
        tmp_path / "d",
        {"tasks/discover.py": declared, "cli/run.py": "from aistack.kernel.runtime import KernelRuntime\n"},
    )

    assert len(audit.measure(registered_only)["registered_tasks_never_executed"]) == 1
    assert audit.measure(resolved)["registered_tasks_never_executed"] == []
    assert audit.measure(asked_for)["registered_tasks_never_executed"] == []
    assert audit.measure(through_the_runtime)["registered_tasks_never_executed"] == []


def test_application_code_that_builds_a_provider_is_a_departure(tmp_path: Path) -> None:
    root = _tree(
        tmp_path,
        {
            "providers/docker/provider.py": "class DockerProvider:\n    pass\n\n\nclass Reading:\n    pass\n",
            "providers/gpu/provider.py": "class NvidiaGpuProvider:\n    pass\n",
            "providers/docker/factory.py": "from .provider import DockerProvider\n\nDockerProvider()\n",
            "cli/health.py": (
                "from aistack.providers.docker.provider import DockerProvider, Reading\n"
                "from aistack.providers import gpu\n\n"
                "DockerProvider().collect()\nDockerProvider()\nReading()\n"
                "gpu.provider.NvidiaGpuProvider()\n"
            ),
            "cli/asks.py": (
                "from aistack.providers.docker.provider import DockerProvider\n\n\n"
                "def run(kernel):\n"
                "    return kernel.registries.providers.get_as('docker', DockerProvider)\n"
            ),
            "kernel/bootstrap/registrations.py": "def build(factory):\n    return factory()\n",
        },
    )

    assert _audit().measure(root)["providers_built_by_application_code"] == [
        "src/aistack/cli/health.py -> DockerProvider",
        "src/aistack/cli/health.py -> NvidiaGpuProvider",
    ]


def test_writing_the_disk_outside_a_transaction_is_a_departure(tmp_path: Path) -> None:
    root = _tree(
        tmp_path,
        {
            "a/text.py": "def f(p):\n    p.write_text('x')\n",
            "a/opened.py": "def f(p):\n    with open(p, 'w') as h:\n        h.write('x')\n",
            "a/path_opened.py": "def f(p):\n    with p.open(mode='a') as h:\n        h.write('x')\n",
            "a/moved.py": "def f(p, q):\n    p.replace(q)\n",
            "a/removed.py": "import os\n\ndef f(p):\n    os.remove(p)\n",
            "a/reads.py": "def f(p):\n    with open(p) as h:\n        return h.read().replace('a', 'b')\n",
            "transaction/executor.py": "def f(p):\n    p.write_text('x')\n",
        },
    )

    assert _audit().measure(root)["disk_writes_outside_a_transaction"] == [
        "src/aistack/a/moved.py",
        "src/aistack/a/opened.py",
        "src/aistack/a/path_opened.py",
        "src/aistack/a/removed.py",
        "src/aistack/a/text.py",
    ]


def test_the_registry_in_the_tree_is_not_a_departure(tmp_path: Path) -> None:
    audit = _audit()
    root = _tree(tmp_path, {"__init__.py": ""})
    registry = root / "docs" / "00-foundation" / "FDN-0012-AIStack-Principles-Registry.md"

    assert audit.measure(root)["principles_missing_from_the_tree"] == [
        "docs/00-foundation/FDN-0012-AIStack-Principles-Registry.md"
    ]
    registry.parent.mkdir(parents=True)
    registry.write_text("# AIStack Principles Registry\n", encoding="utf-8")
    assert audit.measure(root)["principles_missing_from_the_tree"] == []


def test_a_cited_document_that_is_not_in_the_tree_is_a_departure(tmp_path: Path) -> None:
    root = _tree(tmp_path, {"health/score.py": '"""Weights: OPS-0008. Register: GOV-0002."""\n'})
    document = root / "docs" / "04-development" / "OPS-0008-Health-Score-Weights.md"
    document.parent.mkdir(parents=True)
    document.write_text("See ADR-0011.\n", encoding="utf-8")

    assert _audit().measure(root)["documents_cited_and_absent"] == ["ADR-0011", "GOV-0002"]


def test_a_document_the_index_declares_kept_at_the_tag_is_not_a_departure(tmp_path: Path) -> None:
    audit = _audit()
    root = _tree(tmp_path, {"a/b.py": "# STD-0002 forbids it; GOV-0001 and OPS-0009 say more\n"})
    index = root / audit.INDEX
    index.parent.mkdir(parents=True)
    index.write_text(
        "# Foundation\n\n## Kept at the tag\n\n"
        "| Document | Subject |\n|---|---|\n| STD-0002 | Test Artifact Isolation |\n\n"
        "## Elsewhere\n\n| GOV-0001 | not in the section above |\n",
        encoding="utf-8",
    )

    assert audit.measure(root)["documents_cited_and_absent"] == ["GOV-0001", "OPS-0009"]


def test_a_cited_principle_the_registry_does_not_declare_is_a_departure(tmp_path: Path) -> None:
    audit = _audit()
    root = _tree(tmp_path, {"kernel/core.py": "# ARC-P-001, and ARC-P-099 which nobody registered\n"})

    assert audit.measure(root)["principles_cited_and_not_registered"] == []

    registry = root / audit.REGISTRY
    registry.parent.mkdir(parents=True)
    registry.write_text(
        "| ID | Principle | Criticality |\n|----|----|----|\n| ARC-P-001 | Generic Kernel Principle | C3 |\n",
        encoding="utf-8",
    )

    assert audit.measure(root)["principles_cited_and_not_registered"] == ["ARC-P-099"]


def test_the_fixtures_of_this_file_are_not_citations() -> None:
    audit = _audit()

    assert Path(__file__).resolve() == (ROOT / audit.OWN_TEST).resolve()
    assert "ARC-P-099" not in audit.measure(ROOT)["principles_cited_and_not_registered"]


def test_the_report_counts_every_measure(tmp_path: Path) -> None:
    audit = _audit()
    measures = audit.measure(_tree(tmp_path, {"cli/around.py": ""}))

    text = audit.report(measures)

    assert set(audit.TITLES) == set(measures)
    assert "| ARC-P-002 | An entry point never builds the Kernel | 1 |" in text
    assert "- `src/aistack/cli/around.py`" in text
