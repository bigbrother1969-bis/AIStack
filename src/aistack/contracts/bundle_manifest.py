from abc import ABC, abstractmethod


class BundleManifest(ABC):
    """
    Contract for Context Bundle metadata.

    A manifest describes the identity,
    provenance and integrity of a bundle.
    """

    @property
    @abstractmethod
    def bundle_id(self) -> str:
        pass

    @property
    @abstractmethod
    def generated_at(self) -> str:
        pass

    @property
    @abstractmethod
    def source_commit(self) -> str:
        pass

    @property
    @abstractmethod
    def artifact_count(self) -> int:
        pass

    @property
    @abstractmethod
    def format_version(self) -> str:
        pass
