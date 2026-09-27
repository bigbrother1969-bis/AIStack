from __future__ import annotations

from aistack.contracts.health_score import ACTION_REQUIRED, EXCELLENT, TO_WATCH
from aistack.i18n import Translator

# ADR-0010. A health bucket and a domain name are identifiers first —
# `OPS-0008`'s weights are declared against "Services", a score's
# bucket is compared against `EXCELLENT` — and a label on a page
# second. The identifier never changes with the language; only what a
# page shows for it does. These two tables are where one becomes the
# other, instead of every renderer building a catalog key from a
# French string with spaces and slashes in it.
#
# `tests/unit/health/test_labels.py` holds both tables against every
# bucket `aistack.contracts.health_score.BUCKETS` declares and every
# domain name the two health commands build, so a sixth domain added
# without a label is caught there, not on a page.
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
}


def bucket_label(t: Translator, bucket: str) -> str:
    """A score bucket as a page shows it; an unknown bucket unchanged."""

    key = BUCKET_KEYS.get(bucket)
    return t(key) if key is not None else bucket


def domain_label(t: Translator, name: str) -> str:
    """
    A health domain's name as a page shows it. A name no table knows
    is shown as it was declared rather than hidden — the same honest
    default every renderer already holds for text it did not write.
    """

    key = DOMAIN_KEYS.get(name)
    return t(key) if key is not None else name
