from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class RootCauseAnalysis(BaseModel):
    probable_root_cause: str
    supporting_evidence: list[str] = Field(default_factory=list)
    contradictory_evidence: list[str] = Field(default_factory=list)
    alternative_hypotheses: list[dict[str, Any]] = Field(default_factory=list)
    impact: str | None = None
    affected_path: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    confidence_type: Literal["evidence_weighted"] = "evidence_weighted"
    reasoning_summary: str = ""
    observed_facts: list[str] = Field(default_factory=list)
    inference: str = ""
    status: Literal["RCA_READY", "INCONCLUSIVE"] = "RCA_READY"


class Recommendation(BaseModel):
    action: str
    rationale: str
    expected_effect: str
    risk: str = "low"
    requires_approval: bool = True
    reversible: bool = True
