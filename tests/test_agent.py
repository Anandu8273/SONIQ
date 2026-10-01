from __future__ import annotations

import pytest

from agent.agent import InvestigationEngine
from agent.decision import parse_agent_decision
from adapters.mock_adapter import MockSonicAdapter
from backend.config import AppConfig
from rca.engine import render_report


def test_malformed_llm_output_rejected() -> None:
    with pytest.raises(ValueError, match="malformed"):
        parse_agent_decision({"action": "RUN_SHELL", "command": "reboot"})
    with pytest.raises(ValueError, match="malformed"):
        parse_agent_decision({"reason": "oops"})
    with pytest.raises(ValueError):
        parse_agent_decision({"action": "CALL_TOOL", "reason": "missing tool name"})


def test_valid_tool_call_parsed() -> None:
    decision = parse_agent_decision(
        {
            "action": "CALL_TOOL",
            "tool": "get_interface_errors",
            "arguments": {"node": "leaf1", "interface": "Ethernet0"},
            "reason": "Correlate interface errors with packet loss.",
        }
    )
    assert decision.tool == "get_interface_errors"


@pytest.mark.asyncio
async def test_high_latency_investigation_reaches_rca() -> None:
    engine = InvestigationEngine(config=AppConfig(), adapter=MockSonicAdapter("high_latency_leaf1_leaf2"))
    incident = engine.create_incident(
        title="High latency between Leaf-1 and Leaf-2",
        description="Traffic between Leaf-1 and Leaf-2 is experiencing increased latency",
        affected_nodes=["leaf1", "leaf2"],
        source_endpoint="leaf1",
        destination_endpoint="leaf2",
        affected_interfaces=["Ethernet0"],
    )
    investigation = await engine.investigate(incident)
    assert investigation.steps_taken >= 2
    assert investigation.steps_taken <= investigation.max_steps
    assert investigation.evidence
    tools = [c["tool"] for c in investigation.tool_calls]
    assert "get_latency" in tools
    assert "get_packet_loss" in tools
    assert "get_interface_errors" in tools
    assert investigation.rca is not None
    assert investigation.rca.observed_facts
    assert investigation.rca.inference
    assert "definitely" not in investigation.rca.inference.lower()
    report = render_report(investigation)
    assert "OBSERVED FACTS" in report
    assert "INFERENCE" in report
    assert "APPROVAL" in report
    hyp_map = {h.key: h.status.value for h in investigation.hypotheses}
    assert hyp_map["interface_degradation"] in {"weakened", "inconclusive"}
    assert hyp_map["routing_problem"] == "weakened"
    assert hyp_map["bgp_instability"] == "weakened"


@pytest.mark.asyncio
async def test_interface_degradation_scenario_supports_iface() -> None:
    engine = InvestigationEngine(config=AppConfig(), adapter=MockSonicAdapter("interface_degradation_leaf1"))
    incident = engine.create_incident(
        title="Packet loss detected between Leaf-1 and Leaf-2",
        affected_nodes=["leaf1", "leaf2"],
        source_endpoint="leaf1",
        destination_endpoint="leaf2",
        affected_interfaces=["Ethernet0"],
    )
    investigation = await engine.investigate(incident)
    hyp = next(h for h in investigation.hypotheses if h.key == "interface_degradation")
    assert hyp.status.value == "supported"
    assert "Ethernet0" in investigation.rca.probable_root_cause
