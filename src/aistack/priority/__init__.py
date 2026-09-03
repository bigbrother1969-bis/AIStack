"""
Resource priority between front-line and background containers.

Deciding whether Jellyfin is being watched, and what that means for
every other container on the machine, is pure logic living here —
separate from `aistack.providers.jellyfin`, which only observes what
the daemon answered, and separate from whatever applies the decision
through `docker update`, which touches the host.
"""
