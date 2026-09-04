from __future__ import annotations

from dataclasses import dataclass

from aistack.kernel.catalog import Catalog
from aistack.selection.subtree import SubtreeResolution


@dataclass(frozen=True)
class ItemDecision:
    """
    Why one catalog item is included in the selection, or is not.

    `rule` names which of `SubtreeResolution`'s own categories
    decided the item — this adds no new judgment, it names a
    judgment already made and already tested. An item ticked
    directly is a root; one covered because an ancestor was ticked
    is inherited; one ticked but already covered by a ticked
    ancestor is redundant, and still included; anything else was
    never reached and is excluded.
    """

    id: str
    included: bool
    rule: str


def explain_selection(
    catalog: Catalog, resolution: SubtreeResolution
) -> tuple[ItemDecision, ...]:
    """
    Name the rule that decided every item in the catalog — included
    or excluded. `STD-0300` VS-3 criterion 3.2, 2026-09-04.

    **Every catalog item gets a decision, not only the selected
    ones.** The gap this closes was not a missing test: nothing
    represented an excluded item at all — `Selection` carries only
    the ids that were kept, so an item nobody ticked left no trace
    to explain. This walks `catalog.items` instead of the
    selection, so the item that was never touched gets a decision
    too, the same as the one that was.

    **Ticked identifiers absent from the catalog are not covered
    here.** `SubtreeResolution.absent` already names them, and they
    are not catalog items — there is nothing in `catalog.items` to
    attach a decision to. Duplicating that list under a different
    name would be two governed facts for one observation.

    Pure, like the `SubtreeResolution` it reads: no filesystem, no
    randomness, nothing that was not already in `catalog` and
    `resolution`.
    """

    roots = set(resolution.roots)
    redundant = set(resolution.redundant)
    covered = set(resolution.covered)

    parents = {item.id: item.metadata.get("parent", "") for item in catalog.items}

    decisions: list[ItemDecision] = []

    for item in catalog.items:
        if item.id in roots:
            decisions.append(
                ItemDecision(id=item.id, included=True, rule="ticked")
            )
            continue

        if item.id in redundant:
            covering = _covering_root(item.id, roots, parents)
            decisions.append(
                ItemDecision(
                    id=item.id,
                    included=True,
                    rule=f"redundant, already covered by {covering!r}",
                )
            )
            continue

        if item.id in covered:
            covering = _covering_root(item.id, roots, parents)
            decisions.append(
                ItemDecision(
                    id=item.id,
                    included=True,
                    rule=f"inherited from {covering!r}",
                )
            )
            continue

        decisions.append(
            ItemDecision(
                id=item.id,
                included=False,
                rule="excluded, never ticked and no ticked ancestor",
            )
        )

    return tuple(decisions)


def _covering_root(node: str, roots: set[str], parents: dict[str, str]) -> str:
    """
    Walk up by the declared parent, the same way
    `resolve_subtrees._has_ticked_ancestor` does, until a root is
    reached. `roots`' subtrees are disjoint by construction (the
    same fact `resolve_subtrees` documents), so exactly one root
    covers any given covered node — this walk cannot find two.
    """

    seen = {node}
    current = parents.get(node, "")

    while current:
        if current in roots:
            return current

        if current in seen:
            # Same guard as `_has_ticked_ancestor`: a parent chain
            # this catalog cannot produce is not worth an
            # interface, but it must not spin forever.
            break

        seen.add(current)
        current = parents.get(current, "")

    return ""
