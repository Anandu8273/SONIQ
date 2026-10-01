from __future__ import annotations

from datetime import datetime, timezone

from agent.hypotheses import HypothesisManager, RULES, seed_connectivity_hypotheses
from agent.state import HypothesisStatus
from backend.ids import IdFactory
from evidence.models import Evidence, EvidenceType, Significance


def _ev(metric: str, value, baseline=None, significance=Significance.UNKNOWN, evid="EVID-X") -> Evidence:
    return Evidence(
        evidence_id=evid,
        timestamp=datetime.now(timezone.utc),
        node="leaf1",
        interface="Ethernet0",
        evidence_type=EvidenceType.INTERFACE_COUNTER,
        metric=metric,
        value=value,
        baseline=baseline,
        source="mock",
        tool="test",
        significance=significance,
    )


def test_rules_are_inspectable() -> None:
    names = {rule.name for rule in RULES}
    assert "packet_loss_elevated" in names
    assert "bgp_unavailable" in names


def test_interface_errors_strengthen_degradation() -> None:
    hyps = seed_connectivity_hypotheses(IdFactory())
    manager = HypothesisManager(hyps)
    manager.apply_evidence(
        [_ev("rx_errors", 124, 0, Significance.ELEVATED, "EVID-003")]
    )
    hyp = manager.by_key("interface_degradation")
    assert hyp.status == HypothesisStatus.SUPPORTED
    assert "EVID-003" in hyp.evidence_for


def test_zero_errors_weaken_degradation() -> None:
    hyps = seed_connectivity_hypotheses(IdFactory())
    manager = HypothesisManager(hyps)
    manager.apply_evidence([_ev("rx_errors", 0, 0, Significance.NORMAL, "EVID-010")])
    hyp = manager.by_key("interface_degradation")
    assert hyp.status == HypothesisStatus.WEAKENED
    assert "EVID-010" in hyp.evidence_against


def test_unavailable_bgp_does_not_weaken() -> None:
    hyps = seed_connectivity_hypotheses(IdFactory())
    manager = HypothesisManager(hyps)
    manager.apply_evidence(
        [
            Evidence(
                evidence_id="EVID-BGP",
                timestamp=datetime.now(timezone.utc),
                node="leaf1",
                evidence_type=EvidenceType.BGP,
                metric="bgp_availability",
                value="unsupported_or_unavailable",
                source="mock",
                tool="get_bgp_status",
                significance=Significance.UNAVAILABLE,
                confidence="unavailable",
            )
        ]
    )
    hyp = manager.by_key("bgp_instability")
    assert hyp.status == HypothesisStatus.UNTESTED
    assert hyp.evidence_against == []
    assert hyp.evidence_for == []


def test_route_installed_weakens_routing() -> None:
    hyps = seed_connectivity_hypotheses(IdFactory())
    manager = HypothesisManager(hyps)
    manager.apply_evidence(
        [
            Evidence(
                evidence_id="EVID-R",
                timestamp=datetime.now(timezone.utc),
                node="leaf1",
                evidence_type=EvidenceType.ROUTE,
                metric="route_state",
                value="installed",
                source="mock",
                tool="get_route",
                significance=Significance.NORMAL,
            )
        ]
    )
    assert manager.by_key("routing_problem").status == HypothesisStatus.WEAKENED
