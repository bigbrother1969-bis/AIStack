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
    """

    _bundle_id: str
    _generated_at: str
    _source_commit: str
    _artifact_count: int
    _format_version: str = "1.1"
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
