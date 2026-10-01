"""Correlate evidence by time, node, interface, path, and metric. Facts only."""

from __future__ import annotations

from collections import defaultdict

from evidence.models import Evidence, Significance


def correlate(evidence: list[Evidence]) -> dict:
    by_time = sorted(evidence, key=lambda e: e.timestamp)
    by_node: dict[str, list[str]] = defaultdict(list)
    by_interface: dict[str, list[str]] = defaultdict(list)
    by_metric: dict[str, list[str]] = defaultdict(list)
    for item in by_time:
        if item.node:
            by_node[item.node].append(item.evidence_id)
        if item.interface:
            by_interface[item.interface].append(item.evidence_id)
        by_metric[item.metric].append(item.evidence_id)
    observed: list[str] = []
    for item in by_time:
        if item.significance == Significance.UNAVAILABLE:
            continue
        observed.append(_fact_line(item))
    return {
        "ordered_ids": [e.evidence_id for e in by_time],
        "by_node": dict(by_node),
        "by_interface": dict(by_interface),
        "by_metric": dict(by_metric),
        "observed_facts": observed,
    }


def _fact_line(item: Evidence) -> str:
    loc = " ".join(x for x in [item.node, item.interface] if x)
    prefix = f"{loc}: " if loc else ""
    if item.baseline is not None and item.value is not None:
        return f"{prefix}{item.metric} observed {item.value} {item.unit or ''} (baseline {item.baseline}).".replace("  ", " ")
    return f"{prefix}{item.metric} observed {item.value} {item.unit or ''}".strip() + "."
