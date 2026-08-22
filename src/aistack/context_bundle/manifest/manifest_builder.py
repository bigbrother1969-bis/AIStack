from dataclasses import dataclass

from aistack.contracts.bundle_manifest import (
    BundleManifest,
)


@dataclass(frozen=True)
class DefaultBundleManifest(
    BundleManifest
):
    """
    Immutable Context Bundle manifest.

    `format_version` describes the archive layout, not the
    heritage. **1.2**, since 2026-08-22: the archive may carry a
    fifth entry, `contract-inventory.json`, holding the contract
    architecture measured at generation.

    *May*, not *does*. A bundle built without a source tree to
    walk carries no inventory, and the entry is then absent
    rather than empty — an empty one would be indistinguishable
    from a heritage with no contracts, where FDN-0003 Article 12
    makes the absence a state.

    A 1.1 consumer reading a 1.2 archive ignores an entry it does
    not know, and a 1.2 consumer reading a 1.1 archive finds no
    inventory and reports the debt as undeclared. The version
    moves because the layout changed, not because either side
    breaks.

    `content_hash` is unaffected: it is derived from artifact
    identities alone, so a bundle from a mirror stays provably
    equivalent to one from the SPOT. The inventory measures the
    code, not the governed knowledge, and two projections of the
    same heritage built from different working trees are still
    the same projection.
    """

    _bundle_id: str
    _generated_at: str
    _source_commit: str
    _artifact_count: int
    _format_version: str = "1.2"
    _repository_url: str = "unknown"
    _content_hash: str = ""
    _hash_algorithm: str = "sha256"


    @property
    def bundle_id(self) -> str:
        return self._bundle_id


    @property
    def generated_at(self) -> str:
        return self._generated_at


    @property
    def source_commit(self) -> str:
        return self._source_commit


    @property
    def artifact_count(self) -> int:
        return self._artifact_count


    @property
    def format_version(self) -> str:
        return self._format_version


    @property
    def repository_url(self) -> str:
        return self._repository_url


    @property
    def content_hash(self) -> str:
        return self._content_hash


    @property
    def hash_algorithm(self) -> str:
        return self._hash_algorithm
