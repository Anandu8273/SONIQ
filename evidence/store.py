from __future__ import annotations

from evidence.models import Evidence


class EvidenceStore:
    def __init__(self) -> None:
        self._items: dict[str, Evidence] = {}

    def add(self, evidence: Evidence) -> Evidence:
        self._items[evidence.evidence_id] = evidence
        return evidence

    def extend(self, items: list[Evidence]) -> None:
        for item in items:
            self.add(item)

    def get(self, evidence_id: str) -> Evidence | None:
        return self._items.get(evidence_id)

    def list(self, investigation_id: str | None = None) -> list[Evidence]:
        values = list(self._items.values())
        if investigation_id is None:
            return values
        return [e for e in values if e.investigation_id == investigation_id]

    def by_metric(self, metric: str) -> list[Evidence]:
        return [e for e in self._items.values() if e.metric == metric]
