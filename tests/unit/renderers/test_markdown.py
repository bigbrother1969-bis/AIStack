"""`aistack.renderers.markdown`: each construct the manual uses, and nothing injectable."""

from __future__ import annotations

from aistack.renderers.markdown import render


def test_headings_get_anchors_and_are_listed():
    html, headings = render("# Title\n\n## Les bases\n\n### Deux adresses\n")

    assert '<h2 id="les-bases">Les bases</h2>' in html
    assert [(h.level, h.anchor) for h in headings] == [(1, "title"), (2, "les-bases"), (3, "deux-adresses")]


def test_paragraphs_lists_tables_and_code():
    source = """A **bold** and *italic* `code`
continued.

- one
  wrapped
- two

1. first
2. second

| A | B |
|---|---|
| x | `y` |

```
python -m x <subject>
```
"""
    html, _ = render(source)

    assert "<p>A <strong>bold</strong> and <em>italic</em> <code>code</code> continued.</p>" in html
    assert "<ul><li>one wrapped</li><li>two</li></ul>" in html
    assert "<ol><li>first</li><li>second</li></ol>" in html
    assert "<th>A</th>" in html and "<td><code>y</code></td>" in html
    assert "<pre><code>python -m x &lt;subject&gt;</code></pre>" in html


def test_nothing_in_a_source_becomes_markup():
    html, _ = render('<script>alert(1)</script> and **<b>x</b>**')

    assert "<script>" not in html and "<b>" not in html


def test_the_manual_names_no_real_domain():
    """The owner, 2026-10-04: a placeholder, never this deployment's own domain."""

    from aistack.manual import MANUAL_DIR

    for source in MANUAL_DIR.glob("manual.*.md"):
        assert "persiaut-family" not in source.read_text(encoding="utf-8"), source.name
