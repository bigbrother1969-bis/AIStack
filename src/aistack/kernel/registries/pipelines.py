from __future__ import annotations

from aistack.kernel.contracts import KnowledgePipeline


class PipelineRegistry:
    """Registry of governed Knowledge Pipelines."""

    def __init__(self) -> None:
        self._pipelines: dict[str, KnowledgePipeline] = {}

    def register(self, pipeline_id: str, pipeline: KnowledgePipeline) -> None:
        self._pipelines[pipeline_id] = pipeline

    def get(self, pipeline_id: str) -> KnowledgePipeline:
        return self._pipelines[pipeline_id]

    def all(self) -> dict[str, KnowledgePipeline]:
        return dict(self._pipelines)
