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
        raise NotImplementedError

    @property
    @abstractmethod
    def generated_at(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def source_commit(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def artifact_count(self) -> int:
        raise NotImplementedError

    @property
    @abstractmethod
    def format_version(self) -> str:
        raise NotImplementedError
