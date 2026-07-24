from abc import ABC, abstractmethod


class BundleTransferPolicy(ABC):
    """
    Contract defining Context Bundle transfer policy.

    A policy decides whether and where a bundle
    can be transferred.
    """

    @property
    @abstractmethod
    def enabled(self) -> bool:
        pass


    @property
    @abstractmethod
    def target(self) -> str:
        pass


    @property
    @abstractmethod
    def strategy(self) -> str:
        pass
