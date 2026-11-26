"""
Start-up checks (ADR-0032): the controls an owner runs by hand after a
reboot, declared once and judged by code.

This package holds the declaration only (slice B0): what a healthy start
looks like on each machine, which findings weigh what, and the few options
of the indicator and of the morning summary. Nothing here reads a machine
or acts on one; the facts, the verdict, the indicator and the AI choice
come in the next slices.
"""
