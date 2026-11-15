"""
Restart watch (ADR-0025): after a start, bring back the containers that
came up stuck, in the order their dependencies need.

A cold boot starts some seventy containers at once. A few come up
*running* and useless: an s6-supervised image hangs at init and never
starts its web server, or a container sharing another's network
(`network_mode: container:<id>`) keeps the namespace of a provider that
was restarted after it. Docker's restart policy sees neither, since
nothing exited. This package finds them, plans the order, and restarts
them — inside a window after the start, a few times at most.

Pure parts: `detect`, `order`, `guard`. Docker and the clock stay in
`facts`, `act` and `aistack.cli.restart_watch`.
"""
