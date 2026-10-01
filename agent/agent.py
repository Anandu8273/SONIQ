"""Investigation engine. Evidence before action. No one-shot LLM RCA."""

from __future__ import annotations
import asyncio

import logging
from datetime import datetime, timezone

from adapters.base import NetworkAdapter
from adapters.mock_adapter import MockSonicAdapter
from agent.decision import AgentDecision, parse_agent_decision
from agent.hypotheses import HypothesisManager, seed_connectivity_hypotheses
from agent.planner import DeterministicPlanner
from agent.state import Incident, IncidentStatus, Investigation, InvestigationStatus, TimelineEvent
from agent.tool_registry import ToolRegistry, UnknownToolError
from backend.config import AppConfig, load_config
from backend.ids import IdFactory
from evidence.normalizer import EvidenceNormalizer
from evidence.store import EvidenceStore
from rca.engine import RcaEngine, build_recommendation, render_report
from recovery.baseline import extract_symptom_metrics, verify_recovery
from tools.base import ToolResult

logger = logging.getLogger(__name__)


async def run_demo_incident(scenario: str = "high_latency_leaf1_leaf2") -> Investigation:
    """Execute the default mock investigation and return the produced investigation object."""
    engine = build_engine(scenario=scenario)
    incident = engine.create_incident(
        title="High latency between Leaf-1 and Leaf-2",
        description="Traffic between Leaf-1 and Leaf-2 is experiencing increased latency",
        source="manual",
        affected_nodes=["leaf1", "leaf2"],
        affected_interfaces=["Ethernet0"],
        source_endpoint="leaf1",
        destination_endpoint="leaf2",
        severity="medium",
    )
    return await engine.investigate(incident)

class InvestigationEngine:
    def __init__(
        self,
        config: AppConfig | None = None,
        adapter: NetworkAdapter | None = None,
        registry: ToolRegistry | None = None,
    ) -> None:
        self.config = config or load_config()
        self.ids = IdFactory()
        if adapter is None:
            adapter = MockSonicAdapter(self.config.mock.scenario)
        self.adapter = adapter
        self.registry = registry or ToolRegistry(adapter, allow_write=self.config.tools.allow_write)
        self.planner = DeterministicPlanner()
        self.normalizer = EvidenceNormalizer(self.ids)
        self.store = EvidenceStore()
        self.rca_engine = RcaEngine()
        self.investigations: dict[str, Investigation] = {}
        self.incidents: dict[str, Incident] = {}

    def create_incident(self, **kwargs) -> Incident:
        if "incident_id" not in kwargs:
            kwargs["incident_id"] = self.ids.next("INC")
        incident = Incident.model_validate(kwargs)
        self.incidents[incident.incident_id] = incident
        return incident

    async def investigate(self, incident: Incident) -> Investigation:
        investigation = Investigation(
            investigation_id=self.ids.next("INV"),
            incident=incident,
            status=InvestigationStatus.RECEIVED,
            max_steps=self.config.agent.max_steps,
            hypotheses=seed_connectivity_hypotheses(self.ids),
        )
        investigation.add_event(TimelineEvent(event="INCIDENT_RECEIVED", details={"title": incident.title}))
        investigation.status = InvestigationStatus.SCOPING
        investigation.add_event(TimelineEvent(event="HYPOTHESES_INITIALIZED", details={"count": len(investigation.hypotheses)}))
        self.investigations[investigation.investigation_id] = investigation
        incident.status = IncidentStatus.INVESTIGATING

        manager = HypothesisManager(investigation.hypotheses)
        investigation.status = InvestigationStatus.EVIDENCE_COLLECTION

        while investigation.steps_taken < investigation.max_steps:
            raw_decision = self.planner.next_decision(investigation)
            decision = parse_agent_decision(raw_decision.model_dump())
            if decision.action == "FINALIZE_RCA":
                investigation.add_event(TimelineEvent(event="FINALIZE_RCA", details={"reason": decision.reason}))
                break
            if decision.action != "CALL_TOOL" or not decision.tool:
                raise ValueError("planner produced a non-executable action during evidence collection")
            await self._execute_tool_step(investigation, manager, decision)

        self._finalize(investigation)
        return investigation

    async def _execute_tool_step(
        self,
        investigation: Investigation,
        manager: HypothesisManager,
        decision: AgentDecision,
    ) -> ToolResult:
        investigation.steps_taken += 1
        investigation.status = InvestigationStatus.HYPOTHESIS_TESTING
        investigation.add_event(
            TimelineEvent(
                event="TOOL_CALL",
                tool=decision.tool,
                arguments=decision.arguments,
                details={"reason": decision.reason, "step": investigation.steps_taken},
            )
        )
        investigation.tool_calls.append({"tool": decision.tool, "arguments": dict(decision.arguments)})
        logger.info(
            "investigation_tool",
            extra={
                "investigation_id": investigation.investigation_id,
                "tool": decision.tool,
                "node": decision.arguments.get("node"),
                "arguments": decision.arguments,
            },
        )
        try:
            result = await self.registry.execute(decision.tool, decision.arguments)
        except UnknownToolError as exc:
            raise
        except Exception as exc:  # tool execution failures become evidence, not invented state
            result = ToolResult(
                tool=decision.tool or "unknown",
                status="UNAVAILABLE",
                node=decision.arguments.get("node"),
                started_at=datetime.now(timezone.utc),
                ended_at=datetime.now(timezone.utc),
                success=False,
                error=str(exc),
                data={"status": "UNAVAILABLE", "reason": str(exc), "node": decision.arguments.get("node")},
            )
        items = self.normalizer.normalize(result, investigation.investigation_id)
        self.store.extend(items)
        investigation.evidence.extend(items)
        for item in items:
            investigation.add_event(TimelineEvent(event="EVIDENCE_COLLECTED", evidence_id=item.evidence_id, tool=decision.tool))
        for event in manager.apply_evidence(items):
            investigation.add_event(event)
        return result

    def _finalize(self, investigation: Investigation) -> None:
        rca = self.rca_engine.generate(investigation)
        investigation.rca = rca
        investigation.recommendation = build_recommendation(rca)
        if rca.status == "INCONCLUSIVE":
            investigation.status = InvestigationStatus.INCONCLUSIVE
        else:
            investigation.status = InvestigationStatus.RCA_READY
            if self.config.agent.require_approval:
                investigation.status = InvestigationStatus.WAITING_FOR_APPROVAL
        investigation.add_event(TimelineEvent(event="RCA_GENERATED", details={"status": rca.status}))

    def approve(self, investigation_id: str, action: str | None = None) -> Investigation:
        investigation = self.investigations[investigation_id]
        if not investigation.recommendation:
            raise ValueError("no recommendation to approve")
        investigation.approved = True
        investigation.approval_action = action or investigation.recommendation.action
        investigation.add_event(TimelineEvent(event="HUMAN_APPROVED", details={"action": investigation.approval_action}))
        return investigation

    def verify(self, investigation_id: str, metrics_after: dict[str, float] | None = None) -> Investigation:
        investigation = self.investigations[investigation_id]
        if not investigation.approved:
            raise ValueError("human approval is required before verification")
        before = extract_symptom_metrics([e.model_dump() for e in investigation.evidence])
        after = metrics_after or before
        investigation.recovery = verify_recovery(before, after)
        investigation.status = InvestigationStatus.VERIFICATION
        if investigation.recovery.recovery_status.value == "VERIFIED":
            investigation.status = InvestigationStatus.RECOVERED
        investigation.add_event(
            TimelineEvent(
                event="RECOVERY_VERIFIED" if investigation.status == InvestigationStatus.RECOVERED else "RECOVERY_CHECKED",
                details={"status": investigation.recovery.recovery_status.value},
            )
        )
        return investigation

    def report_text(self, investigation: Investigation) -> str:
        return render_report(investigation)


def build_engine(scenario: str | None = None) -> InvestigationEngine:
    config = load_config()
    if scenario:
        config.mock.scenario = scenario
    adapter = MockSonicAdapter(config.mock.scenario)
    return InvestigationEngine(config=config, adapter=adapter)

def main() -> None:
    """Run the default SONIQ incident workflow and print the final report."""
    investigation = asyncio.run(run_demo_incident())
    print(render_report(investigation))


if __name__ == "__main__":
    main()
