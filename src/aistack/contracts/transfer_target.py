from abc import ABC, abstractmethod


class TransferTarget(ABC):
    """
    Contract describing a bundle transfer destination.
    """

    @property
    @abstractmethod
    def host(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def user(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def path(self) -> str:
        raise NotImplementedError
