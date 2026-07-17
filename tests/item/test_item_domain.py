"""Tests for the Governed Item domain."""

import unittest
from datetime import datetime, timezone

from aistack.item import (
    GovernedItem,
    Item,
    ItemAlreadyRegisteredError,
    ItemLifecycle,
    ItemLifecycleStatus,
    ItemMetadata,
    ItemNotFoundError,
    ItemRegistry,
)


class GovernedItemDomainTests(unittest.TestCase):
    def setUp(self) -> None:
        self.item = Item(
            item_id="item:test:001",
            item_type="test",
            metadata=ItemMetadata(
                owner="AIStack",
                provenance="unit-test",
                trust_score=1.0,
            ),
            lifecycle=ItemLifecycle(
                status=ItemLifecycleStatus.ACTIVE,
                effective_at=datetime.now(timezone.utc),
            ),
        )

    def test_item_satisfies_governed_item_interface(self) -> None:
        self.assertIsInstance(self.item, GovernedItem)

    def test_registry_registers_and_returns_item(self) -> None:
        registry = ItemRegistry()

        registry.register(self.item)

        self.assertEqual(registry.get(self.item.item_id), self.item)
        self.assertTrue(registry.contains(self.item.item_id))
        self.assertEqual(len(registry), 1)

    def test_registry_rejects_identity_replacement(self) -> None:
        registry = ItemRegistry()
        registry.register(self.item)

        with self.assertRaises(ItemAlreadyRegisteredError):
            registry.register(self.item)

    def test_registry_reports_unknown_item(self) -> None:
        registry = ItemRegistry()

        with self.assertRaises(ItemNotFoundError):
            registry.get("item:unknown")

    def test_trust_score_is_bounded(self) -> None:
        with self.assertRaises(ValueError):
            ItemMetadata(
                owner="AIStack",
                provenance="unit-test",
                trust_score=1.1,
            )


if __name__ == "__main__":
    unittest.main()
