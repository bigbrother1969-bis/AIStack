from render_engine.core import Renderer
from render_engine.renderers.html import HtmlRenderer


class RenderRegistry:
    def __init__(self) -> None:
        self._renderers: dict[str, Renderer] = {}

    def register(self, renderer: Renderer) -> None:
        self._renderers[renderer.format] = renderer

    def get(self, format_name: str) -> Renderer:
        if format_name not in self._renderers:
            raise KeyError(f"No renderer registered for format: {format_name}")
        return self._renderers[format_name]


def default_registry() -> RenderRegistry:
    registry = RenderRegistry()
    registry.register(HtmlRenderer())
    return registry
