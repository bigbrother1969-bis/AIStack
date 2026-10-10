from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from aistack.kernel.catalog import Catalog


@dataclass(frozen=True)
class SubtreeResolution:
    """What a set of ticked nodes designates.

    - `roots`: ticked nodes with no ticked ancestor; their subtrees are
      disjoint.
    - `covered`: every node reached, ticked or inherited from an ancestor.
    - `redundant`: ticked nodes already covered by a ticked ancestor.
    - `absent`: ticked ids the catalog no longer holds (deleted since the
      selection was saved), shown rather than ignored.
    - `media_files`/`media_bytes`: summed over `roots`, so each file
      counts once.
    """

    roots: tuple[str, ...]
    covered: tuple[str, ...]
    redundant: tuple[str, ...]
    absent: tuple[str, ...]
    media_files: int
    media_bytes: int


def resolve_subtrees(
    catalog: Catalog, selected_ids: Iterable[str]
) -> SubtreeResolution:
    """Resolve ticked identifiers against the catalog.

    A ticked identifier designates a whole subtree. Pure (no filesystem
    access), so the screen and the generator share one interpretation of
    the ticks.
    """

    known = {item.id: item for item in catalog.items}

    ticked = sorted(set(selected_ids))

    absent = tuple(node for node in ticked if node not in known)

    present = [node for node in ticked if node in known]

    ancestors = set(present)

    roots: list[str] = []
    redundant: list[str] = []

    for node in present:

        if _has_ticked_ancestor(node, known, ancestors):
            redundant.append(node)
            continue

        roots.append(node)

    covered: list[str] = []
    files = 0
    size = 0

    children = _children(catalog)

    for root in roots:
        files += _number(known[root].metadata.get("total_media_files"))
        size += _number(known[root].metadata.get("total_media_bytes"))

        covered.extend(_descendants(root, children))

    return SubtreeResolution(
        roots=tuple(roots),
        covered=tuple(sorted(set(covered))),
        redundant=tuple(redundant),
        absent=absent,
        media_files=files,
        media_bytes=size,
    )


def _has_ticked_ancestor(
    node: str,
    known: Mapping[str, object],
    ticked: set[str],
) -> bool:
    """Whether an ancestor of `node` is ticked, walking the declared
    `parent` metadata rather than splitting the id (ids need not be paths).

    `known` is a `Mapping` (covariant) so a `dict[str, CatalogItem]` can be
    passed.
    """

    seen = {node}

    current = _parent_of(known.get(node))

    while current:

        if current in seen:
            # A cyclic parent chain: stop. Checked before `ticked`, or a
            # node in a cycle would count as its own ancestor.
            return False

        if current in ticked:
            return True

        seen.add(current)

        current = _parent_of(known.get(current))

    return False


def _children(catalog: Catalog) -> dict[str, list[str]]:
    children: dict[str, list[str]] = {}

    for item in catalog.items:
        children.setdefault(item.metadata.get("parent", ""), []).append(item.id)

    return children


def _descendants(root: str, children: dict[str, list[str]]) -> list[str]:
    found = [root]

    stack = list(children.get(root, []))

    while stack:
        node = stack.pop()

        if node in found:
            continue

        found.append(node)

        stack.extend(children.get(node, []))

    return found


def _parent_of(item: object) -> str:
    metadata = getattr(item, "metadata", None)

    return metadata.get("parent", "") if metadata else ""


def _number(value: str | None) -> int:
    """Parse a count stored as text; a malformed value reads as zero so the
    screen still renders."""

    try:
        return int(value or 0)

    except ValueError:
        return 0
