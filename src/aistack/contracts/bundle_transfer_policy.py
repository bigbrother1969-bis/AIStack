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
        raise NotImplementedError


    @property
    @abstractmethod
    def target(self) -> str:
        raise NotImplementedError


    @property
    @abstractmethod
    def strategy(self) -> str:
        raise NotImplementedError
