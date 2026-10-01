from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RecoveryStatus(str, Enum):
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"


class RecoveryResult(BaseModel):
    recovery_status: RecoveryStatus
    verification_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metrics_before: dict[str, Any] = Field(default_factory=dict)
    metrics_after: dict[str, Any] = Field(default_factory=dict)
    changed_metrics: list[str] = Field(default_factory=list)
    remaining_symptoms: list[str] = Field(default_factory=list)
    conclusion: str
