"""
The Cybersecurity Manager's assessment (ADR-0028).

Read-only: it reads what the host already shows (the listening sockets,
the ports Docker publishes) and says what it found, with its evidence and
what it could not read. It changes nothing on any host.
"""
