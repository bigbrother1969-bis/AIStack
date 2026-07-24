from abc import ABC, abstractmethod


class BundleTransferConfiguration(ABC):
    """
    Contract describing where and how a Context Bundle
    must be transferred.
    """

    @property
    @abstractmethod
    def enabled(self) -> bool:
        pass


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
    def destination_path(self) -> str:
        pass
