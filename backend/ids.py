"""Deterministic sequential IDs for a process (INC/INV/EVID/HYP)."""

from __future__ import annotations

from collections import defaultdict


class IdFactory:
    def __init__(self) -> None:
        self._counters: dict[str, int] = defaultdict(int)

    def next(self, prefix: str) -> str:
        self._counters[prefix] += 1
        return f"{prefix}-{self._counters[prefix]:03d}"
