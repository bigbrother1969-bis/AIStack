from __future__ import annotations

import re

from aistack.contracts.runtime_observation import RuntimeObservation


_HTTP_REQUEST_LINE = re.compile(
    r'"(GET|POST|PUT|DELETE|HEAD|PATCH|OPTIONS|CONNECT|TRACE) '
    r'\S+ HTTP/\d\.\d"'
)


def no_incoming_requests(observation: RuntimeObservation) -> bool:
    """
    Whether the observed log window carries no evidence of an
    incoming HTTP request.

    `STD-0300` § VS-4's reference incident lists "no incoming HTTP
    requests" among the evidence that made `aistack-selection-ui`'s
    permanent `--reload` energy inefficiency rather than legitimate
    work (`OPS-0004`) — this makes that evidence checkable rather
    than asserted.

    The pattern matched is the common ("combined") HTTP access-log
    line format nginx, Apache and most application servers emit
    alike — the exact shape `firefly`'s own log carried when
    `OPS-0004`'s reference case was investigated. `GOV-P-001` does
    not govern this: it is a published logging convention, not an
    owner's operational fact, the same standing `extract_dockerfile_
    command`'s `CMD` parsing already holds.

    **What this does not prove.** A container logging nothing in
    this shape within the observed window is not proof no request
    arrived — a service that logs requests differently, or not at
    all, reads the same way. What this confirms is narrower and
    purely observed: no line in this window matches the shape an
    incoming HTTP request takes in the overwhelming majority of
    web-serving containers. It says nothing about an active browser
    session, which the reference incident also lists and which this
    function does not check.
    """

    return not any(
        _HTTP_REQUEST_LINE.search(entry.text)
        for entry in observation.entries
    )
