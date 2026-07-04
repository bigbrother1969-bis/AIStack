from html import escape

from render_engine.core import RenderInput, RenderOutput


class HtmlRenderer:
    format = "html"

    def render(self, source: RenderInput) -> RenderOutput:
        body = escape(str(source.content)).replace("\n", "<br>\n")

        html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{escape(source.title)}</title>
</head>
<body>
  <main>
    <h1>{escape(source.title)}</h1>
    <section>
      {body}
    </section>
  </main>
</body>
</html>
"""

        return RenderOutput(
            artifact_id=source.artifact_id,
            format=self.format,
            content=html,
        )
