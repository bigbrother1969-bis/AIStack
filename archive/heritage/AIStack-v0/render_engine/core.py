from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Any


@dataclass(frozen=True)
class RenderInput:
    artifact_id: str
    title: str
    content: Any
    metadata: dict[str, Any]


@dataclass(frozen=True)
class RenderOutput:
    artifact_id: str
    format: str
    content: str


class Renderer(Protocol):
    format: str

    def render(self, source: RenderInput) -> RenderOutput:
        ...
