from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from aistack.kernel.catalog import Catalog


@dataclass(frozen=True)
class SubtreeResolution:
    """
    What a set of ticked nodes actually designates.

    Five statements, and each answers a question the screen or the
    generator would otherwise have to answer by guessing.

    `roots` are the ticked nodes with no ticked ancestor. They are
    the selection, minimally expressed: their subtrees are
    disjoint by construction, which is what makes `media_bytes`
    exact rather than approximately right.

    `covered` is every node the selection reaches, ticked or
    inherited. The screen needs it to show a node as taken because
    an ancestor was ticked, which is the whole point of ticking at
    the height you mean — decided 2026-08-29 by the owner.

    `redundant` are ticked nodes already covered by a ticked
    ancestor. Ticking `Classique` then `Classique/Bach` is not an
    error and nothing is dropped; but it is worth saying, because
    unticking `Classique` would then leave Bach behind and the
    human should be able to see that coming.

    `absent` are ticked identifiers the catalog no longer holds.
    The library is scanned at every request — decided 2026-08-29 —
    so a directory deleted on the server disappears from the
    catalog while remaining in the saved selection. It must be
    shown as *selected but absent*, never ignored in silence and
    never left to fail later in the generator.

    `media_files` and `media_bytes` count each file once. A parent
    and its child both ticked is the case that makes a naive sum
    wrong, and a capacity bar that double-counts on a 64 Go quota
    is worse than no capacity bar.
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
    """
    Resolve ticked identifiers against the catalog that offers them.

    **A ticked identifier designates a subtree**, not a directory
    and not a file — the owner's decision of 2026-08-29, taken
    because his tree is five levels deep and holds media at all
    five. So resolving is not a lookup: it is deciding which ticks
    still exist, which ones cover which, and what the whole
    designates.

    Pure, and deliberately so. It touches no filesystem: the
    catalog carries what the walk observed, so this can be tested
    on a catalog built by hand, and the generator that follows can
    be handed a resolution rather than a list of ticks to
    re-interpret. Two consumers interpreting the same ticks
    differently is the shape this heritage keeps removing.
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
    known: dict[str, object],
    ticked: set[str],
) -> bool:
    """
    Walk up by the declared parent, not by splitting the path.

    The identifier is a relative path and splitting it on the
    separator would agree with the parent metadata in every case
    this library has produced. It would stop agreeing the day an
    identifier is not a path — the catalog builder for a different
    source is the second member of the family the owner decided on
    2026-08-29 — and it would fail silently, on the one screen
    whose subject is what is taken and what is left.
    """

    seen = {node}

    current = _parent_of(known.get(node))

    while current:

        if current in seen:
            # A parent chain that closes on itself is not
            # something this catalog can produce, and not
            # something worth hanging an interface for.
            #
            # Tested before it was written the right way round: the
            # first version asked whether the ancestor was ticked
            # before asking whether it had already been visited,
            # so a node whose chain came back round to itself was
            # its own ancestor and disappeared from the roots.
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
    """
    `CatalogItem.metadata` is `dict[str, str]`, so a count arrives
    as text. A malformed one is read as zero rather than raising:
    the screen must still render, and a weight that is wrong is
    visible where a stack trace is not.
    """

    try:
        return int(value or 0)

    except ValueError:
        return 0
