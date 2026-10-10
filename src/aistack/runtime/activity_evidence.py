from __future__ import annotations

import re

from aistack.contracts.runtime_observation import RuntimeObservation


_HTTP_REQUEST_LINE = re.compile(
    r'"(GET|POST|PUT|DELETE|HEAD|PATCH|OPTIONS|CONNECT|TRACE) '
    r'\S+ HTTP/\d\.\d"'
)


def no_incoming_requests(observation: RuntimeObservation) -> bool:
    """
    Return True when no log line in the observed window looks like an incoming
    HTTP request in the common ("combined") access-log format.

    This does not prove that no request arrived: a service that logs requests
    differently, or not at all, reads the same way.
    """

    return not any(
        _HTTP_REQUEST_LINE.search(entry.text)
        for entry in observation.entries
    )
