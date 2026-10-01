"""Pydantic-validated agent actions. Arbitrary shell is never a valid action."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError, field_validator


class CallToolAction(BaseModel):
    action: Literal["CALL_TOOL"]
    tool: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    reason: str


class FinalizeRcaAction(BaseModel):
    action: Literal["FINALIZE_RCA"]
    reason: str


class RequestHumanApprovalAction(BaseModel):
    action: Literal["REQUEST_HUMAN_APPROVAL"]
    reason: str


class AgentDecision(BaseModel):
    action: Literal["CALL_TOOL", "FINALIZE_RCA", "REQUEST_HUMAN_APPROVAL"]
    tool: str | None = None
    arguments: dict[str, Any] = Field(default_factory=dict)
    reason: str

    @field_validator("tool")
    @classmethod
    def tool_required_for_call(cls, value: str | None, info: Any) -> str | None:
        return value

    def as_typed(self) -> CallToolAction | FinalizeRcaAction | RequestHumanApprovalAction:
        if self.action == "CALL_TOOL":
            if not self.tool:
                raise ValueError("CALL_TOOL requires a registered tool name")
            return CallToolAction(action="CALL_TOOL", tool=self.tool, arguments=self.arguments, reason=self.reason)
        if self.action == "FINALIZE_RCA":
            return FinalizeRcaAction(action="FINALIZE_RCA", reason=self.reason)
        return RequestHumanApprovalAction(action="REQUEST_HUMAN_APPROVAL", reason=self.reason)


def parse_agent_decision(payload: dict[str, Any]) -> AgentDecision:
    try:
        decision = AgentDecision.model_validate(payload)
    except ValidationError as exc:
        raise ValueError(f"malformed agent decision: {exc}") from exc
    if decision.action == "CALL_TOOL" and not decision.tool:
        raise ValueError("malformed agent decision: CALL_TOOL missing tool")
    return decision
