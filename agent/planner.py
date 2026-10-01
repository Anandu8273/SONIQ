"""Deterministic planner used when LLM tool-calling is disabled.

Selects the most useful unread diagnostic based on remaining hypotheses.
This is not a fixed one-shot RCA: the next tool depends on current evidence.
"""

from __future__ import annotations

from agent.decision import AgentDecision
from agent.state import HypothesisStatus, Investigation
from evidence.models import Evidence, Significance


CORE_TOOLS = {
    "get_latency",
    "get_packet_loss",
    "get_interface_errors",
    "get_interface_stats",
    "get_route",
    "get_bgp_status",
}


class DeterministicPlanner:
    def next_decision(self, investigation: Investigation) -> AgentDecision:
        if _ready_to_finalize(investigation):
            return AgentDecision(action="FINALIZE_RCA", reason="Sufficient core evidence collected; hypotheses can be separated.")
        source, dest = _endpoints(investigation)
        def unused(tool: str, arguments: dict) -> bool:
            for call in investigation.tool_calls:
                if call["tool"] != tool:
                    continue
                if all(call["arguments"].get(key) == value for key, value in arguments.items()):
                    return False
            return True

        if unused("get_latency", {"node": source, "destination": dest}):
            return AgentDecision(
                action="CALL_TOOL",
                tool="get_latency",
                arguments={"node": source, "destination": dest},
                reason="Measure path latency to confirm the reported symptom with an observation.",
            )
        if unused("get_packet_loss", {"node": source, "destination": dest}):
            return AgentDecision(
                action="CALL_TOOL",
                tool="get_packet_loss",
                arguments={"node": source, "destination": dest},
                reason="Determine whether packet loss accompanies the latency symptom.",
            )
        if unused("get_interface_errors", {"node": source}):
            return AgentDecision(
                action="CALL_TOOL",
                tool="get_interface_errors",
                arguments={"node": source, "interface": _interface(investigation)},
                reason="Test interface/data-plane error counters on the source node.",
            )
        if _errors_elevated(investigation.evidence) and unused("get_interface_errors", {"node": dest}):
            return AgentDecision(
                action="CALL_TOOL",
                tool="get_interface_errors",
                arguments={"node": dest, "interface": _interface(investigation)},
                reason="Source-side errors were elevated; compare the peer interface.",
            )
        if unused("get_interface_stats", {"node": source}):
            return AgentDecision(
                action="CALL_TOOL",
                tool="get_interface_stats",
                arguments={"node": source, "interface": _interface(investigation)},
                reason="Check operational status of the source interface.",
            )
        if unused("get_route", {"node": source}):
            return AgentDecision(
                action="CALL_TOOL",
                tool="get_route",
                arguments={"node": source, "destination": dest},
                reason="Test whether the route toward the destination remains installed.",
            )
        if unused("get_bgp_status", {"node": source}):
            return AgentDecision(
                action="CALL_TOOL",
                tool="get_bgp_status",
                arguments={"node": source},
                reason="Test BGP session state as an alternative to data-plane failure.",
            )
        if unused("get_logs", {"node": source}):
            return AgentDecision(
                action="CALL_TOOL",
                tool="get_logs",
                arguments={"node": source, "since_seconds": 300, "max_lines": 50},
                reason="Collect a bounded log summary after core metrics.",
            )
        if unused("get_config", {"node": source}):
            return AgentDecision(
                action="CALL_TOOL",
                tool="get_config",
                arguments={"node": source},
                reason="Read-only configuration check for inconsistency.",
            )
        if unused("get_asic_state", {"node": source}):
            return AgentDecision(
                action="CALL_TOOL",
                tool="get_asic_state",
                arguments={"node": source},
                reason="Queue/ASIC telemetry may explain latency without errors; query if available.",
            )
        if unused("get_platform_health", {"node": source}):
            return AgentDecision(
                action="CALL_TOOL",
                tool="get_platform_health",
                arguments={"node": source},
                reason="Platform sensors may explain forwarding degradation if exposed.",
            )
        return AgentDecision(action="FINALIZE_RCA", reason="No unused diagnostic tools remain that are likely to reduce uncertainty.")


def _endpoints(investigation: Investigation) -> tuple[str, str]:
    incident = investigation.incident
    nodes = incident.affected_nodes or ["leaf1", "leaf2"]
    source = incident.source_endpoint or nodes[0]
    dest = incident.destination_endpoint or (nodes[1] if len(nodes) > 1 else nodes[0])
    return source, dest


def _interface(investigation: Investigation) -> str:
    ifaces = investigation.incident.affected_interfaces
    return ifaces[0] if ifaces else "Ethernet0"


def _errors_elevated(evidence: list[Evidence]) -> bool:
    return any(e.metric in {"rx_errors", "crc_errors"} and e.significance == Significance.ELEVATED for e in evidence)


def _core_metrics_present(evidence: list[Evidence]) -> set[str]:
    present: set[str] = set()
    mapping = {
        "latency_avg": "get_latency",
        "packet_loss_pct": "get_packet_loss",
        "rx_errors": "get_interface_errors",
        "oper_status": "get_interface_stats",
        "route_state": "get_route",
        "bgp_session_state": "get_bgp_status",
        "bgp_availability": "get_bgp_status",
    }
    for item in evidence:
        tool = mapping.get(item.metric)
        if tool:
            present.add(tool)
    return present


def _ready_to_finalize(investigation: Investigation) -> bool:
    present = _core_metrics_present(investigation.evidence)
    if not CORE_TOOLS.issubset(present) and investigation.steps_taken < investigation.max_steps:
        missing = set(CORE_TOOLS) - present
        if missing and missing != {"get_bgp_status"}:
            return False
        if "get_bgp_status" in missing:
            return False
    tested = [h for h in investigation.hypotheses if h.status != HypothesisStatus.UNTESTED]
    if len(tested) < 4:
        return False
    supported = [h for h in investigation.hypotheses if h.status == HypothesisStatus.SUPPORTED]
    weakened = [h for h in investigation.hypotheses if h.status == HypothesisStatus.WEAKENED]
    if supported and len(weakened) >= 2:
        return True
    if CORE_TOOLS.issubset(present) and len(tested) >= 5:
        return True
    return False
