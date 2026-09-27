from __future__ import annotations

from typing import Iterable

from aistack.timemachine.graph import Literal


def is_user_data_path(candidate: str, user_data_roots: Iterable[str]) -> bool:
    """
    `True` if `candidate` names a path under any of `user_data_roots`
    — matches the root itself and anything below it, but never a
    sibling that merely shares its prefix (`"/mnt/nextcloudX"` does
    not match a root of `"/mnt/nextcloud"`).
    """

    for root in user_data_roots:
        stripped = root.rstrip("/")
        if candidate == stripped or candidate.startswith(f"{stripped}/"):
            return True

    return False


def filter_fact(
    subject: str,
    obj: str | Literal,
    user_data_roots: Iterable[str] = (),
) -> bool:
    """
    `ADR-0011` § *Decision* 6's projection filter — the pass the ADR
    names `aistack.timemachine.projection.filter`. `True` keeps a
    fact, `False` drops it outright before it ever reaches the
    store: masking a user-data path still proves it exists and
    roughly where; dropping does not.

    A fact is dropped when its subject, or an IRI it points at as
    its object, names a path under a declared user-data root — R2's
    own example, a Nextcloud or Immich file path, never configuration
    or binaries. A `Literal` object is never itself a path (nothing
    this projection writes puts a filesystem path in a literal
    value), so only a bare `str` object is checked.

    `user_data_roots` is empty by default because nothing in this
    codebase states one yet, measured 2026-09-27: none of the streams
    `aistack.timemachine.projection.project_observation_history`
    walks today collects a fact whose subject or object is a user's
    own file — `NextcloudProvider`'s own WebDAV observations are not
    wired into Observation History at all. A caller passes real roots
    once a collector that is (1.5's concern, `ADR-0011` § *Open
    Points*) states what shape its subjects take.
    """

    if is_user_data_path(subject, user_data_roots):
        return False

    if isinstance(obj, str) and is_user_data_path(obj, user_data_roots):
        return False

    return True
