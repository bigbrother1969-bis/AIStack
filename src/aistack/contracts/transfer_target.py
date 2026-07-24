from abc import ABC, abstractmethod


class TransferTarget(ABC):
    """
    Contract describing a bundle transfer destination.
    """

    @property
    @abstractmethod
    def host(self) -> str:
        pass

    @property
    @abstractmethod
    def user(self) -> str:
        pass

    @property
    @abstractmethod
    def path(self) -> str:
        pass
