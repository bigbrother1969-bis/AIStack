"""
The power the GPU draws while a call runs, read from `nvidia-smi` when the process can see it.

Best effort, and never in the way of a question: no `nvidia-smi`, no driver, a card that reports `[N/A]` or
a slow answer give `None`, and the calculation then uses the declared power (`footprint.yml`).
"""

from __future__ import annotations

import subprocess
import threading
from collections.abc import Callable

READ_TIMEOUT = 3.0
SAMPLE_EVERY = 0.5

Reader = Callable[[], float | None]


def read_gpu_watts() -> float | None:
    """The power drawn now by all the GPUs together, in watts; `None` when it cannot be read."""

    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=power.draw", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=READ_TIMEOUT,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    if result.returncode != 0:
        return None

    total = 0.0
    seen = 0

    for line in result.stdout.splitlines():
        if not line.strip():
            continue

        try:
            total += float(line.strip())
        except ValueError:
            return None

        seen += 1

    return round(total, 2) if seen else None


class PowerSampler:
    """
    Reads the GPU power every `SAMPLE_EVERY` seconds while a call runs. The reading made on entry only says
    whether the power can be read; it is not counted, because it is taken before the card works. `mean()` is
    the average of the readings made during the call, or `None` when there was none.
    """

    def __init__(self, reader: Reader = read_gpu_watts, every: float = SAMPLE_EVERY) -> None:
        self._reader = reader
        self._every = every
        self._samples: list[float] = []
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def __enter__(self) -> "PowerSampler":
        try:
            readable = self._reader() is not None
        except Exception:  # the question goes on whatever the reader does
            readable = False

        if readable:
            self._thread = threading.Thread(target=self._run, name="gpu-power", daemon=True)
            self._thread.start()

        return self

    def __exit__(self, *_: object) -> None:
        self._stop.set()

        if self._thread is not None:
            self._thread.join(timeout=READ_TIMEOUT + 1)

    def _run(self) -> None:
        while not self._stop.wait(self._every):
            try:
                value = self._reader()
            except Exception:
                return

            if value is not None:
                self._samples.append(value)

    def mean(self) -> float | None:
        samples = list(self._samples)

        return round(sum(samples) / len(samples), 2) if samples else None
