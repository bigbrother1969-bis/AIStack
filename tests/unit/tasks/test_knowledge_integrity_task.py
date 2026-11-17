from __future__ import annotations

import json
from pathlib import Path

from aistack.kernel.execution import Request
from aistack.tasks.knowledge_integrity import KnowledgeIntegrityTask


def _bundle(tmp_path: Path, content: str) -> Path:
    payload = {
        "id": "test-bundle",
        "title": "Test Bundle",
        "generated_at": "2026-08-21T00:00:00",
        "source_commit": "abc1234",
        "artifacts": [
            {
                "id": "a",
                "title": "A decision",
                "source": "docs/a.md",
                "content": content,
            }
        ],
    }
    path = tmp_path / "bundle.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _execute(bundle: Path) -> dict:
    request = Request(request_id="r", task_id="knowledge.integrity", payload={"bundle": str(bundle)})
    return KnowledgeIntegrityTask().execute(request).data


def test_the_task_returns_what_the_checks_observed(tmp_path: Path) -> None:
    data = _execute(_bundle(tmp_path, "# no frontmatter\n"))

    assert data["bundle_id"] == "test-bundle"
    assert data["source_commit"] == "abc1234"
    assert data["artifact_count"] == 1
    assert data["blocking"] >= 1
    assert data["clean"] is False
    assert all(
        set(item) == {"check", "severity", "summary", "affected", "total", "unit", "subjects"}
        for item in data["findings"]
    )
    assert {item["severity"] for item in data["findings"]} <= {"blocking", "warning", "observation"}


def test_the_task_writes_nothing(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path, "# no frontmatter\n")
    before = sorted(path.name for path in tmp_path.iterdir())

    _execute(bundle)

    assert sorted(path.name for path in tmp_path.iterdir()) == before
