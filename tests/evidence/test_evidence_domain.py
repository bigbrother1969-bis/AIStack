import unittest
from datetime import datetime, timezone

from aistack.evidence import Evidence
from aistack.item import ItemLifecycle, ItemMetadata


class EvidenceTests(unittest.TestCase):

    def test_create_evidence(self):
        evidence = Evidence(
            item_id="docker:1",
            item_type="docker.container",
            source="docker",
            metadata=ItemMetadata(
                owner="AIStack",
                provenance="docker",
            ),
            lifecycle=ItemLifecycle(
                effective_at=datetime.now(timezone.utc),
            ),
        )

        self.assertEqual(evidence.source, "docker")


if __name__ == "__main__":
    unittest.main()
