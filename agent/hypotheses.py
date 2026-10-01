"""Deterministic hypothesis seeding and evidence-weighted updates.

Rules are explicit. Unavailable measurements do not count as negative evidence.
"""

from __future__ import annotations

from dataclasses import dataclass

from agent.state import Hypothesis, HypothesisStatus, TimelineEvent
from backend.ids import IdFactory
from evidence.models import Evidence, Significance


CONNECTIVITY_HYPOTHESES: list[dict[str, str]] = [
    {
        "key": "interface_degradation",
        "title": "Interface degradation",
        "description": "Data-plane errors or discards on an interface degrade forwarding quality.",
        "next_test": "get_interface_errors",
    },
    {
        "key": "packet_loss",
        "title": "Packet loss",
        "description": "End-to-end packet loss is present on the affected path.",
        "next_test": "get_packet_loss",
    },
    {
        "key": "routing_problem",
        "title": "Routing problem",
        "description": "A required route is missing, changed, or unusable.",
        "next_test": "get_route",
    },
    {
        "key": "bgp_instability",
        "title": "BGP instability",
        "description": "BGP session state is not established or is flapping.",
        "next_test": "get_bgp_status",
    },
    {
        "key": "congestion_latency",
        "title": "Congestion/latency issue",
        "description": "Path delay is elevated; congestion is possible but not proven by latency alone.",
        "next_test": "get_latency",
    },
    {
        "key": "link_failure",
        "title": "Link failure",
        "description": "An interface operational state is down.",
        "next_test": "get_interface_stats",
    },
    {
        "key": "configuration_inconsistency",
        "title": "Configuration inconsistency",
        "description": "Relevant configuration differs from the expected healthy baseline.",
        "next_test": "get_config",
    },
]


@dataclass(frozen=True)
class HypothesisRule:
    name: str
    description: str


RULES: list[HypothesisRule] = [
    HypothesisRule("packet_loss_elevated", "IF packet_loss > baseline THEN strengthen packet-loss-related hypothesis."),
    HypothesisRule("packet_loss_zero", "IF packet_loss observed at 0 THEN weaken packet-loss-related hypothesis."),
    HypothesisRule("interface_errors_elevated", "IF interface errors significantly increase THEN strengthen interface degradation."),
    HypothesisRule("interface_errors_zero", "IF interface errors observed at baseline THEN weaken interface degradation."),
    HypothesisRule("bgp_not_established", "IF BGP state is not established THEN strengthen BGP instability."),
    HypothesisRule("bgp_established", "IF BGP session remains established THEN weaken BGP instability."),
    HypothesisRule("bgp_unavailable", "IF BGP is unavailable THEN do not treat as negative evidence."),
    HypothesisRule("route_missing", "IF route disappears THEN strengthen routing failure."),
    HypothesisRule("route_present", "IF route remains installed THEN weaken routing failure."),
    HypothesisRule("oper_down", "IF oper_status is down THEN strengthen link failure."),
    HypothesisRule("oper_up", "IF oper_status is up THEN weaken link failure."),
    HypothesisRule(
        "latency_only",
        "IF latency increases but packet loss and interface errors remain normal THEN investigate congestion/path behavior; do not declare interface failure.",
    ),
]


def seed_connectivity_hypotheses(ids: IdFactory) -> list[Hypothesis]:
    seeded: list[Hypothesis] = []
    for spec in CONNECTIVITY_HYPOTHESES:
        seeded.append(
            Hypothesis(
                hypothesis_id=ids.next("HYP"),
                title=spec["title"],
                description=spec["description"],
                status=HypothesisStatus.UNTESTED,
                confidence=0.0,
                next_test=spec["next_test"],
                key=spec["key"],
            )
        )
    return seeded


class HypothesisManager:
    def __init__(self, hypotheses: list[Hypothesis]) -> None:
        self.hypotheses = hypotheses

    def by_key(self, key: str) -> Hypothesis:
        for hyp in self.hypotheses:
            if hyp.key == key:
                return hyp
        raise KeyError(key)

    def apply_evidence(self, items: list[Evidence]) -> list[TimelineEvent]:
        events: list[TimelineEvent] = []
        for item in items:
            events.extend(self._apply_one(item))
        self._latency_only_adjustment(items)
        return events

    def _apply_one(self, item: Evidence) -> list[TimelineEvent]:
        if item.significance == Significance.UNAVAILABLE or item.confidence == "unavailable":
            return []
        events: list[TimelineEvent] = []
        if item.metric == "packet_loss_pct" and _is_number(item.value):
            if float(item.value) > float(item.baseline or 0):
                events.append(self._strengthen("packet_loss", item, 0.35))
                events.append(self._strengthen("interface_degradation", item, 0.1))
            else:
                events.append(self._weaken("packet_loss", item, 0.25))
        if item.metric in {"rx_errors", "tx_errors", "crc_errors", "drops", "discards"} and _is_number(item.value):
            baseline = float(item.baseline or 0)
            if float(item.value) > baseline:
                events.append(self._strengthen("interface_degradation", item, 0.4))
            elif item.baseline is not None:
                events.append(self._weaken("interface_degradation", item, 0.08))
        if item.metric == "bgp_session_state":
            if item.value == "established":
                events.append(self._weaken("bgp_instability", item, 0.3))
            elif item.value:
                events.append(self._strengthen("bgp_instability", item, 0.5))
        if item.metric == "route_state":
            if item.value == "installed":
                events.append(self._weaken("routing_problem", item, 0.3))
            else:
                events.append(self._strengthen("routing_problem", item, 0.4))
        if item.metric == "route_present" and item.value is False:
            events.append(self._strengthen("routing_problem", item, 0.5))
        if item.metric == "oper_status":
            if item.value == "down":
                events.append(self._strengthen("link_failure", item, 0.6))
            elif item.value == "up":
                events.append(self._weaken("link_failure", item, 0.3))
        if item.metric == "latency_avg" and _is_number(item.value) and item.baseline is not None:
            if float(item.value) > float(item.baseline):
                events.append(self._strengthen("congestion_latency", item, 0.25))
            else:
                events.append(self._weaken("congestion_latency", item, 0.2))
        if item.metric == "log_summary" and item.value and "error" in str(item.value).lower():
            events.append(self._strengthen("interface_degradation", item, 0.1))
        if item.metric == "config_snapshot":
            events.append(self._weaken("configuration_inconsistency", item, 0.05))
        return [e for e in events if e is not None]

    def _latency_only_adjustment(self, items: list[Evidence]) -> None:
        latency_high = any(
            e.metric == "latency_avg" and _is_number(e.value) and e.baseline is not None and float(e.value) > float(e.baseline)
            for e in items
        )
        errors_elevated = any(
            e.metric in {"rx_errors", "crc_errors", "drops"} and e.significance == Significance.ELEVATED for e in items
        )
        loss_elevated = any(e.metric == "packet_loss_pct" and e.significance == Significance.ELEVATED for e in items)
        if latency_high and not errors_elevated:
            self._cap_if_untested_errors()
        if latency_high and not errors_elevated and not loss_elevated:
            hyp = self.by_key("congestion_latency")
            if hyp.confidence > 0.55:
                hyp.confidence = 0.55

    def _cap_if_untested_errors(self) -> None:
        iface = self.by_key("interface_degradation")
        if iface.status == HypothesisStatus.UNTESTED:
            return
        if iface.status == HypothesisStatus.SUPPORTED and iface.confidence < 0.4:
            iface.status = HypothesisStatus.WEAKENED

    def _strengthen(self, key: str, item: Evidence, amount: float) -> TimelineEvent:
        hyp = self.by_key(key)
        old = hyp.status.value
        if item.evidence_id not in hyp.evidence_for:
            hyp.evidence_for.append(item.evidence_id)
        hyp.confidence = min(1.0, hyp.confidence + amount)
        hyp.status = HypothesisStatus.SUPPORTED if hyp.confidence >= 0.35 else HypothesisStatus.INCONCLUSIVE
        return TimelineEvent(
            event="HYPOTHESIS_UPDATED",
            hypothesis=key,
            old_status=old,
            new_status=hyp.status.value,
            evidence_id=item.evidence_id,
        )

    def _weaken(self, key: str, item: Evidence, amount: float) -> TimelineEvent:
        hyp = self.by_key(key)
        old = hyp.status.value
        if item.evidence_id not in hyp.evidence_against:
            hyp.evidence_against.append(item.evidence_id)
        hyp.confidence = max(0.0, hyp.confidence - amount)
        if hyp.confidence <= 0.15:
            hyp.status = HypothesisStatus.WEAKENED
        elif hyp.status == HypothesisStatus.UNTESTED:
            hyp.status = HypothesisStatus.INCONCLUSIVE
        return TimelineEvent(
            event="HYPOTHESIS_UPDATED",
            hypothesis=key,
            old_status=old,
            new_status=hyp.status.value,
            evidence_id=item.evidence_id,
        )


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)
