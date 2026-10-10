from __future__ import annotations

from aistack.contracts.health_score import ACTION_REQUIRED, EXCELLENT, TO_WATCH
from aistack.i18n import Translator

# ADR-0010. Buckets and domain names are identifiers that never change with
# the language; these tables map them to catalog keys for display.
# `tests/unit/health/test_labels.py` checks that every bucket and every
# domain has a label.
BUCKET_KEYS: dict[str, str] = {
    EXCELLENT: "health.bucket.excellent",
    TO_WATCH: "health.bucket.to_watch",
    ACTION_REQUIRED: "health.bucket.action_required",
}

DOMAIN_KEYS: dict[str, str] = {
    "Stockage": "health.domain.storage",
    "Services": "health.domain.services",
    "Sauvegarde / PRA": "health.domain.backup",
    "GPU": "health.domain.gpu",
    "Tests PRA": "health.domain.pra_tests",
    "État persistant": "health.domain.uncovered_state",
    "Écarts d'inventaire": "health.domain.inventory_gap",
    "Hôtes": "health.domain.hosts",
    "Données d'AIStack": "health.domain.data_budget",
}


def bucket_label(t: Translator, bucket: str) -> str:
    """A score bucket as a page shows it; an unknown bucket unchanged."""

    key = BUCKET_KEYS.get(bucket)
    return t(key) if key is not None else bucket


def domain_label(t: Translator, name: str) -> str:
    """
    A health domain's name as a page shows it; an unknown name is shown as
    declared.
    """

    key = DOMAIN_KEYS.get(name)
    return t(key) if key is not None else name
