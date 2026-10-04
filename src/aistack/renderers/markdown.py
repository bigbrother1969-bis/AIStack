"""
A small Markdown renderer for AIStack's own hand-written pages (the user
manual) — headings with anchors, paragraphs, bullet and numbered lists,
tables, fenced code, inline code, bold, italics. Every character of the
source is escaped before any markup is added: nothing in a source can
inject HTML. Not a general Markdown implementation, on purpose: it
renders what this repository writes, and a test pins each construct.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from aistack.renderers.text import escape_text


@dataclass(frozen=True)
class Heading:
    level: int
    text: str
    anchor: str


def slug(text: str) -> str:
    lowered = re.sub(r"[`*]", "", text).lower()
    return re.sub(r"[^\w]+", "-", lowered, flags=re.UNICODE).strip("-")


def inline(text: str) -> str:
    """Escape `text`, then add code, bold and italics."""

    parts = re.split(r"(`[^`]+`)", text)
    out = []
    for part in parts:
        if part.startswith("`") and part.endswith("`") and len(part) > 1:
            out.append(f"<code>{escape_text(part[1:-1])}</code>")
            continue
        escaped = escape_text(part)
        escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
        escaped = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", escaped)
        out.append(escaped)
    return "".join(out)


def _table(rows: list[str]) -> str:
    cells = [[cell.strip() for cell in row.strip().strip("|").split("|")] for row in rows]
    head, body = cells[0], [row for row in cells[2:]]
    html = ["<table>", "<thead><tr>" + "".join(f"<th>{inline(cell)}</th>" for cell in head) + "</tr></thead>", "<tbody>"]
    for row in body:
        html.append("<tr>" + "".join(f"<td>{inline(cell)}</td>" for cell in row) + "</tr>")
    html += ["</tbody>", "</table>"]
    return "\n".join(html)


def render(source: str) -> tuple[str, list[Heading]]:
    """The HTML of `source`, and its headings (for a table of contents)."""

    lines = source.splitlines()
    html: list[str] = []
    headings: list[Heading] = []
    paragraph: list[str] = []
    index = 0

    def flush() -> None:
        if paragraph:
            html.append(f"<p>{inline(' '.join(paragraph))}</p>")
            paragraph.clear()

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()

        if stripped.startswith("```"):
            flush()
            index += 1
            code = []
            while index < len(lines) and not lines[index].strip().startswith("```"):
                code.append(lines[index])
                index += 1
            html.append(f"<pre><code>{escape_text(chr(10).join(code))}</code></pre>")
            index += 1
            continue

        heading = re.match(r"^(#{1,3})\s+(.*)$", stripped)
        if heading:
            flush()
            level, text = len(heading.group(1)), heading.group(2).strip()
            anchor = slug(text)
            headings.append(Heading(level, text, anchor))
            html.append(f'<h{level} id="{anchor}">{inline(text)}</h{level}>')
            index += 1
            continue

        if stripped.startswith("|"):
            flush()
            rows = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                rows.append(lines[index])
                index += 1
            html.append(_table(rows))
            continue

        bullet = re.match(r"^(-|\d+\.)\s+(.*)$", stripped)
        if bullet:
            flush()
            ordered = bullet.group(1) != "-"
            items: list[str] = []
            while index < len(lines):
                current = lines[index]
                match = re.match(r"^(-|\d+\.)\s+(.*)$", current.strip())
                if match and not current.startswith("  "):
                    items.append(match.group(2))
                elif current.strip() and current.startswith(" ") and items:
                    items[-1] += " " + current.strip()
                else:
                    break
                index += 1
            tag = "ol" if ordered else "ul"
            html.append(f"<{tag}>" + "".join(f"<li>{inline(item)}</li>" for item in items) + f"</{tag}>")
            continue

        if not stripped:
            flush()
        else:
            paragraph.append(stripped)
        index += 1

    flush()
    return "\n".join(html), headings
