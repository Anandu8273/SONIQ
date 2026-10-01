from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field

from evidence.models import Evidence
from rca.report import Recommendation, RootCauseAnalysis
from recovery.verifier import RecoveryResult


class IncidentStatus(str, Enum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    VERIFYING = "verifying"
    RESOLVED = "resolved"
    INCONCLUSIVE = "inconclusive"


class InvestigationStatus(str, Enum):
    RECEIVED = "RECEIVED"
    SCOPING = "SCOPING"
    EVIDENCE_COLLECTION = "EVIDENCE_COLLECTION"
    HYPOTHESIS_TESTING = "HYPOTHESIS_TESTING"
    RCA_READY = "RCA_READY"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    VERIFICATION = "VERIFICATION"
    RECOVERED = "RECOVERED"
    INCONCLUSIVE = "INCONCLUSIVE"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Incident(BaseModel):
    incident_id: str
    title: str
    description: str = ""
    source: str = "manual"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    affected_nodes: list[str] = Field(default_factory=list)
    affected_interfaces: list[str] = Field(default_factory=list)
    source_endpoint: str | None = None
    destination_endpoint: str | None = None
    severity: Severity = Severity.MEDIUM
    status: IncidentStatus = IncidentStatus.OPEN


class TimelineEvent(BaseModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    event: str
    tool: str | None = None
    arguments: dict[str, Any] | None = None
    evidence_id: str | None = None
    hypothesis: str | None = None
    old_status: str | None = None
    new_status: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class Investigation(BaseModel):
    investigation_id: str
    incident: Incident
    status: InvestigationStatus = InvestigationStatus.RECEIVED
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    steps_taken: int = 0
    max_steps: int = 10
    evidence: list[Evidence] = Field(default_factory=list)
    hypotheses: list[Any] = Field(default_factory=list)
    timeline: list[TimelineEvent] = Field(default_factory=list)
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    rca: RootCauseAnalysis | None = None
    recommendation: Recommendation | None = None
    recovery: RecoveryResult | None = None
    approved: bool = False
    approval_action: str | None = None

    def add_event(self, event: TimelineEvent) -> None:
        self.timeline.append(event)


class HypothesisStatus(str, Enum):
    UNTESTED = "untested"
    SUPPORTED = "supported"
    WEAKENED = "weakened"
    REJECTED = "rejected"
    INCONCLUSIVE = "inconclusive"


class Hypothesis(BaseModel):
    hypothesis_id: str
    title: str
    description: str
    status: HypothesisStatus = HypothesisStatus.UNTESTED
    evidence_for: list[str] = Field(default_factory=list)
    evidence_against: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    confidence_type: Literal["evidence_weighted"] = "evidence_weighted"
    next_test: str | None = None
    key: str
