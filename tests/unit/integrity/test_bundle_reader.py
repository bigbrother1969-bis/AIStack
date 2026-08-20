import json
import zipfile

from aistack.integrity.bundle_reader import read_bundle


PAYLOAD = {
    "id": "aistack-context-2026-08-14",
    "title": "AIStack Context Bundle",
    "generated_at": "2026-08-14T15:23:06.126769",
    "source_commit": "f88f113",
    "artifacts": [
        {
            "id": "hash1",
            "title": "FDN-0009",
            "domain": "Knowledge Assets",
            "semantic_type": "Knowledge Artifact",
            "criticality": 1,
            "owner": "Foundation",
            "status": "Proposed",
            "confidence": "unknown",
            "source": "docs/00-foundation/FDN-0009.md",
            "content": "# Body\n",
        }
    ],
}


def test_reads_a_bundle_json(tmp_path):

    path = tmp_path / "bundle.json"
    path.write_text(json.dumps(PAYLOAD), encoding="utf-8")

    bundle = read_bundle(path)

    assert bundle.source_commit == "f88f113"
    assert len(bundle.artifacts) == 1
    assert bundle.artifacts[0].status == "Proposed"
    assert bundle.artifacts[0].criticality == "C1"


def test_reads_a_bundle_archive(tmp_path):
    """
    A consumer holding only the published archive must be
    able to verify it, with no access to the repository.
    """

    archive = tmp_path / "bundle.zip"

    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("bundle.json", json.dumps(PAYLOAD))

    bundle = read_bundle(archive)

    assert bundle.id == "aistack-context-2026-08-14"
    assert bundle.artifacts[0].owner == "Foundation"


def test_absent_fields_read_as_unknown(tmp_path):
    """
    A bundle produced before f88f113 carries no status. It
    must read as unknown, never as a fabricated default.
    """

    legacy = dict(PAYLOAD)
    legacy["artifacts"] = [
        {
            k: v
            for k, v in PAYLOAD["artifacts"][0].items()
            if k not in ("status", "confidence", "owner")
        }
    ]

    path = tmp_path / "legacy.json"
    path.write_text(json.dumps(legacy), encoding="utf-8")

    artifact = read_bundle(path).artifacts[0]

    assert artifact.status == "unknown"
    assert artifact.criticality == "C1"
    assert artifact.confidence == "unknown"
    assert artifact.owner == "unknown"
