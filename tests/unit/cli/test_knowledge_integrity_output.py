from pathlib import Path
import json
import subprocess
import sys


ROOT = Path(__file__).parents[3]


def _run(bundle: Path) -> str:
    result = subprocess.run(
        [sys.executable, "-m", "aistack.cli.knowledge_integrity", str(bundle)],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env={"PYTHONPATH": "src", "PATH": "/usr/bin:/bin"},
    )
    return result.stdout


COMPLETE = """---
artifact:
  id: FDN-0009
  title: AI Collaboration Protocol
  type: Foundation Protocol
  semantic_type: Policy
  domain: Foundation
  criticality: C3
  confidence: Reviewed
  version: 1.0
  status: Published
  owner: Foundation
  created: 2026-07-06
  updated: 2026-08-21
---

# Body
"""


def _bundle(tmp_path: Path, content: str) -> Path:
    payload = {
        "id": "test-bundle",
        "title": "Test Bundle",
        "generated_at": "2026-08-21T00:00:00",
        "source_commit": "abc1234",
        "artifacts": [
            {
                "id": "a",
                "title": "AI Collaboration Protocol",
                "type": "Foundation Protocol",
                "semantic_type": "Policy",
                "domain": "Foundation",
                "criticality": "C3",
                "owner": "Foundation",
                "status": "Published",
                "confidence": "Reviewed",
                "source": "docs/00-foundation/FDN-0009.md",
                "content": content,
            }
        ],
    }

    path = tmp_path / "bundle.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    return path


def test_a_clean_report_states_its_verdict(tmp_path):
    """
    A clean run used to print "No finding." and stop, so the one
    line a CI job and a human both look for — `clean: True` —
    appeared only when something was wrong.

    Silence is not a verdict. The report says so either way.
    """

    output = _run(_bundle(tmp_path, COMPLETE))

    assert "No finding." in output
    assert "blocking: 0   warnings: 0   clean: True" in output


def test_a_deficient_report_states_its_verdict(tmp_path):

    output = _run(_bundle(tmp_path, "# no frontmatter\n"))

    assert "No finding." not in output
    assert "clean: False" in output
