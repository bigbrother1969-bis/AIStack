from abc import ABC, abstractmethod

from aistack.contracts.bundle_manifest import (
    BundleManifest,
)


class ManifestSerializer(ABC):
    """
    Contract for serializing bundle manifests.
    """

    @abstractmethod
    def serialize(
        self,
        manifest: BundleManifest,
    ) -> str:
        raise NotImplementedError
