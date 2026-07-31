from abc import ABC, abstractmethod


class ReadmeExporter(ABC):
    """
    Contract for generating Context Bundle README.
    """

    @abstractmethod
    def export(self) -> str:
        raise NotImplementedError
