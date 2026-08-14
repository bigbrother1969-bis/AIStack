from abc import ABC, abstractmethod


class BundleManifest(ABC):
    """
    Contract for Context Bundle metadata.

    A manifest describes the identity,
    provenance and integrity of a bundle.

    Integrity properties allow any consumer to verify
    that a bundle faithfully represents the governed
    heritage of a given source commit, without needing
    access to the repository itself.
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

    @property
    @abstractmethod
    def repository_url(self) -> str:
        """
        Canonical location of the governance SPOT.

        The bundle is a projection. This property states
        which repository the projection was taken from.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def content_hash(self) -> str:
        """
        Fingerprint of the governed knowledge carried by
        the bundle.

        Computed from artifact identities only, so it is
        independent of generation time. Two bundles sharing
        a content_hash carry exactly the same knowledge.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def hash_algorithm(self) -> str:
        raise NotImplementedError
