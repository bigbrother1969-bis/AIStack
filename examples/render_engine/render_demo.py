from pathlib import Path

from render_engine.core import RenderInput
from render_engine.registry import default_registry


source = RenderInput(
    artifact_id="render-engine-demo",
    title="Render Engine Demo",
    content="Governed knowledge can be rendered into disposable artifacts.",
    metadata={
        "owner": "AIStack",
        "status": "demo",
    },
)

renderer = default_registry().get("html")
output = renderer.render(source)

out = Path("examples/render_engine/render-engine-demo.html")
out.write_text(output.content)

print(f"Generated: {out}")
