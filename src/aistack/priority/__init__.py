"""
Resource priority between front-line and background containers.

Deciding whether a priority app is in use, and what that means for every
other container, is pure logic here; `aistack.providers.jellyfin` only
observes, and `docker update` is applied elsewhere.
"""
