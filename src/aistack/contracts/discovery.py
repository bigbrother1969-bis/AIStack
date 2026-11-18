from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DiscoveryResult:
    """
    Immutable result of a knowledge discovery operation.

    Discovery only observes existing sources.
    It does not classify or interpret knowledge.
    """

    # Relative to the root that was searched, with forward slashes
    # (GOV-0002/OS-096): where the file is in the heritage, not
    # where the heritage was when it was read.
    path: Path
    content: str
    content_hash: str
