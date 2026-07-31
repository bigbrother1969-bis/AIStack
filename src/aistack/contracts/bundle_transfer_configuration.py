from abc import ABC, abstractmethod


class BundleTransferConfiguration(ABC):
    """
    Contract describing where and how a Context Bundle
    must be transferred.
    """

    @property
    @abstractmethod
    def enabled(self) -> bool:
        raise NotImplementedError


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
    def destination_path(self) -> str:
        raise NotImplementedError
