from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DiscoveryResult:
    """
    Immutable result of a knowledge discovery operation.

    Discovery only observes existing sources.
    It does not classify or interpret knowledge.
    """

    path: Path
    content: str
    content_hash: str
