"""
Declare a container in `service_categorization.yml` on the owner's click.

The file is the owner's, with comments and a layout of their own, so it
is edited as text, never re-dumped: one service is inserted after the last
service of its category (or a category is added at the end), a dated copy
is kept beside the file, and the result is read back by the real loader
before it replaces the original. If anything is off the original stays.
"""

from __future__ import annotations

import enum
import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path

import yaml

from aistack.architecture.yaml import load_service_categorization_yaml
from aistack.arrivals.propose import service_lines

CATEGORIES_LINE = re.compile(r"^categories:\s*(\[\s*\])?\s*(#.*)?$")
ITEM = re.compile(r"^(\s*)-\s+name:")


class Outcome(enum.Enum):
    DECLARED = "declared"
    ALREADY = "already"
    NO_CATEGORY = "no_category"
    UNSUPPORTED = "unsupported"
    INVALID = "invalid"


def declare_container(
    path: Path,
    *,
    name: str,
    container: str,
    description: str,
    category: str,
    new_category: bool,
    now: datetime,
) -> Outcome:
    name, container, category = name.strip(), container.strip(), category.strip()

    if not name or not container or not category:
        return Outcome.INVALID

    try:
        text = path.read_text(encoding="utf-8")
        data = yaml.safe_load(text) or {}
    except (OSError, yaml.YAMLError):
        return Outcome.UNSUPPORTED

    categories = data.get("categories") if isinstance(data, dict) else None

    if categories is not None and not isinstance(categories, list):
        return Outcome.UNSUPPORTED

    for existing in categories or []:
        for service in (existing or {}).get("services") or []:
            if (service or {}).get("container") == container:
                return Outcome.ALREADY

    names = [str((entry or {}).get("name")) for entry in categories or []]

    if not new_category and category not in names:
        return Outcome.NO_CATEGORY

    if new_category and category in names:
        new_category = False

    lines = text.split("\n")
    edited = _insert_in_category(lines, category, name, container, description) if not new_category else (
        _append_category(lines, category, name, container, description)
    )

    if edited is None:
        return Outcome.UNSUPPORTED

    return _replace(path, text, "\n".join(edited), container, now)


def _top(lines: list[str]) -> tuple[int, bool] | None:
    """The line of `categories:` and whether it reads `categories: []`."""

    for index, line in enumerate(lines):
        match = CATEGORIES_LINE.match(line)

        if match:
            return index, bool(match.group(1))

    return None


def _category_starts(lines: list[str], top: int) -> tuple[str, list[int]]:
    """The indent of the category items and the index of each one."""

    indent: str | None = None
    starts: list[int] = []

    for index in range(top + 1, len(lines)):
        line = lines[index]

        if not line.strip() or line.lstrip().startswith("#"):
            continue

        match = ITEM.match(line)

        if indent is None:
            if not match:
                break

            indent = match.group(1)

        if match and match.group(1) == indent:
            starts.append(index)
        elif not line.startswith(indent + " ") and not line.startswith(indent + "-"):
            break

    return indent or "  ", starts


def _insert_in_category(lines: list[str], category: str, name: str, container: str, description: str) -> list[str] | None:
    found = _top(lines)

    if found is None or found[1]:
        return None

    indent, starts = _category_starts(lines, found[0])

    for position, start in enumerate(starts):
        title = yaml.safe_load(lines[start].split("name:", 1)[1].strip() or "''")

        if str(title) != category:
            continue

        end = starts[position + 1] if position + 1 < len(starts) else len(lines)
        services = [
            index
            for index in range(start + 1, end)
            if (match := ITEM.match(lines[index])) and len(match.group(1)) > len(indent)
        ]

        if not services:
            return None

        first = ITEM.match(lines[services[0]])
        assert first is not None
        last = _last_content_line(lines, services[0], end)

        return lines[: last + 1] + service_lines(first.group(1), name, container, description) + lines[last + 1 :]

    return None


def _append_category(lines: list[str], category: str, name: str, container: str, description: str) -> list[str] | None:
    found = _top(lines)

    if found is None:
        return None

    top, empty = found
    indent, _ = _category_starts(lines, top)
    block = [f"{indent}- name: {json.dumps(category, ensure_ascii=False)}", f"{indent}  services:"]
    block += service_lines(indent + "    ", name, container, description)

    if empty:
        return lines[:top] + ["categories:"] + block + lines[top + 1 :]

    last = _last_content_line(lines, top, len(lines))

    return lines[: last + 1] + block + lines[last + 1 :]


def _last_content_line(lines: list[str], start: int, end: int) -> int:
    """The last line in `[start, end)` that is neither blank nor a comment."""

    return max(index for index in range(start, end) if lines[index].strip() and not lines[index].lstrip().startswith("#"))


def _replace(path: Path, before: str, after: str, container: str, now: datetime) -> Outcome:
    if not after.endswith("\n"):
        after += "\n"

    temporary = path.with_name(path.name + ".arrivals.tmp")

    try:
        temporary.write_text(after, encoding="utf-8")
        declared = load_service_categorization_yaml(temporary)

        if not any(s.container == container for c in declared.categories for s in c.services):
            raise ValueError("the container is not in the edited file")

        shutil.copy2(path, path.with_name(f"{path.name}.avant-arrivals-{now:%Y%m%d-%H%M%S}"))
        os.replace(temporary, path)
    except (OSError, ValueError, yaml.YAMLError):
        temporary.unlink(missing_ok=True)

        return Outcome.INVALID

    return Outcome.DECLARED
