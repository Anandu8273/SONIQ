"""Evidence-weighted RCA. Separates observed facts from inference. Does not invent measurements."""

from __future__ import annotations

from agent.state import HypothesisStatus, Investigation
from evidence.correlation import correlate
from evidence.models import Evidence, Significance
from rca.confidence import evidence_weighted_confidence
from rca.report import Recommendation, RootCauseAnalysis


class RcaEngine:
    def generate(self, investigation: Investigation) -> RootCauseAnalysis:
        facts = _observed_facts(investigation.evidence)
        ranked = sorted(investigation.hypotheses, key=lambda h: h.confidence, reverse=True)
        leading = ranked[0] if ranked else None
        alternatives = []
        for hyp in ranked[1:]:
            alternatives.append(
                {
                    "title": hyp.title,
                    "status": hyp.status.value,
                    "reason": _alt_reason(hyp, investigation.evidence),
                    "confidence": hyp.confidence,
                }
            )
        supporting = list(leading.evidence_for) if leading else []
        contradictory = list(leading.evidence_against) if leading else []
        if leading is None or (
            leading.status in {HypothesisStatus.UNTESTED, HypothesisStatus.INCONCLUSIVE} and leading.confidence < 0.2
        ):
            inference = (
                "Evidence remains insufficient to name a probable root cause. "
                "Missing or unavailable telemetry is not treated as a negative finding."
            )
            return RootCauseAnalysis(
                probable_root_cause="Insufficient evidence for a probable root cause.",
                supporting_evidence=supporting,
                contradictory_evidence=contradictory,
                alternative_hypotheses=alternatives,
                impact=investigation.incident.title,
                affected_path=_path(investigation),
                confidence=0.0,
                reasoning_summary=inference,
                observed_facts=facts,
                inference=inference,
                status="INCONCLUSIVE",
            )
        inference = _inference(leading, investigation.evidence)
        return RootCauseAnalysis(
            probable_root_cause=_cause_text(leading, investigation),
            supporting_evidence=supporting,
            contradictory_evidence=contradictory,
            alternative_hypotheses=alternatives,
            impact=investigation.incident.title,
            affected_path=_path(investigation),
            confidence=evidence_weighted_confidence(leading.confidence),
            reasoning_summary=inference,
            observed_facts=facts,
            inference=inference,
            status="RCA_READY",
        )


def build_recommendation(rca: RootCauseAnalysis) -> Recommendation:
    if rca.status == "INCONCLUSIVE":
        return Recommendation(
            action="Collect additional telemetry (queue/ASIC/platform) and re-run investigation. No disruptive change.",
            rationale="A probable root cause was not established from available evidence.",
            expected_effect="Narrow remaining hypotheses without changing the data plane.",
            risk="none",
            requires_approval=True,
            reversible=True,
        )
    if rca.probable_root_cause.startswith("Interface/data-plane"):
        return Recommendation(
            action="Inspect the affected interface and restore normal link operation. No automated shutdown.",
            rationale=rca.inference,
            expected_effect="Error counters and path quality return toward baseline.",
            risk="medium if a link is taken out of service",
            requires_approval=True,
            reversible=True,
        )
    return Recommendation(
        action="Continue non-disruptive path/latency investigation; do not change routing, BGP, or interfaces automatically.",
        rationale=rca.inference,
        expected_effect="Additional evidence or operator inspection of the path.",
        risk="low",
        requires_approval=True,
        reversible=True,
    )


def render_report(investigation: Investigation) -> str:
    rca = investigation.rca
    rec = investigation.recommendation
    if rca is None:
        return "No RCA has been generated."
    lines = [
        "==================================================",
        "SONIQ INVESTIGATION REPORT",
        "==================================================",
        "",
        f"Incident:\n{investigation.incident.title}",
        "",
        f"Investigation ID:\n{investigation.investigation_id}",
        "",
        f"Status:\n{investigation.status.value}",
        "",
        "PROBABLE ROOT CAUSE:",
        rca.probable_root_cause,
        "",
        "OBSERVED FACTS:",
    ]
    for i, fact in enumerate(rca.observed_facts, 1):
        lines.append(f"{i}. {fact}")
    lines += ["", "SUPPORTING EVIDENCE:"]
    lines.extend(rca.supporting_evidence or ["(none)"])
    lines += ["", "ALTERNATIVE HYPOTHESES:"]
    for alt in rca.alternative_hypotheses:
        lines.append(f"{alt.get('title')}:")
        lines.append(str(alt.get('status', '')).upper())
        lines.append(f"Reason:\n{alt.get('reason', '')}")
        lines.append("")
    lines += [
        "INFERENCE:",
        rca.inference,
        "",
        "RECOMMENDATION:",
        rec.action if rec else "",
        "",
        "APPROVAL:",
        "REQUIRED" if rec is None or rec.requires_approval else "NOT REQUIRED",
        "",
        "CONFIDENCE TYPE:",
        rca.confidence_type,
        f"evidence-weighted score: {rca.confidence:.2f} (not a calibrated probability)",
    ]
    return "\n".join(lines)


def _observed_facts(evidence: list[Evidence]) -> list[str]:
    facts = correlate(evidence)["observed_facts"]
    compact: list[str] = []
    seen: set[str] = set()
    for fact in facts:
        key = fact.split(" observed ")[0] if " observed " in fact else fact
        if key in seen and "rx_packets" in fact:
            continue
        if any(skip in fact for skip in ("rx_packets", "tx_packets", "rx_bytes", "tx_bytes", "config_snapshot")):
            continue
        seen.add(key)
        compact.append(fact)
    return compact[:12]


def _path(investigation: Investigation) -> list[str]:
    nodes = investigation.incident.affected_nodes
    return nodes or ["leaf1", "leaf2"]


def _cause_text(leading, investigation: Investigation) -> str:
    iface = None
    for item in investigation.evidence:
        if item.metric == "rx_errors" and item.significance == Significance.ELEVATED:
            iface = f"{item.node} {item.interface}"
            break
    if leading.key == "interface_degradation":
        where = f" on {iface}" if iface else ""
        return f"Interface/data-plane degradation{where}"
    if leading.key == "congestion_latency":
        return (
            "Elevated path latency without observed interface errors, packet loss, routing loss, or BGP failure. "
            "Congestion or external path delay is the leading hypothesis; queue/ASIC telemetry was not available to confirm."
        )
    return leading.title


def _inference(leading, evidence: list[Evidence]) -> str:
    if leading.key == "interface_degradation":
        return (
            "The observed increase in interface errors coinciding with packet loss and/or latency degradation "
            "supports the interface/data-plane degradation hypothesis. This is not a claim of certainty."
        )
    if leading.key == "congestion_latency":
        return (
            "Latency is elevated relative to baseline while packet loss, interface error counters, installed routes, "
            "and BGP sessions (where available) do not show a corresponding failure. That pattern is consistent with "
            "path delay or congestion, but latency alone does not prove a congestion root cause."
        )
    return f"The evidence-weighted standing of '{leading.title}' is the strongest among tested hypotheses."


def _alt_reason(hyp, evidence: list[Evidence]) -> str:
    if hyp.key == "routing_problem" and hyp.status == HypothesisStatus.WEAKENED:
        return "Route remained present during the investigation."
    if hyp.key == "bgp_instability" and hyp.status == HypothesisStatus.WEAKENED:
        return "BGP session remained established."
    if hyp.key == "interface_degradation" and hyp.status == HypothesisStatus.WEAKENED:
        return "Interface error counters remained at baseline."
    if hyp.key == "packet_loss" and hyp.status == HypothesisStatus.WEAKENED:
        return "Packet loss was observed at 0%."
    if hyp.key == "link_failure" and hyp.status == HypothesisStatus.WEAKENED:
        return "Interface operational status remained up."
    if hyp.status == HypothesisStatus.UNTESTED:
        return "Hypothesis was not strongly tested by collected evidence."
    return hyp.description
