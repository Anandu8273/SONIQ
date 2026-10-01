from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class EvidenceType(str, Enum):
    INTERFACE_COUNTER = "interface_counter"
    INTERFACE_STATUS = "interface_status"
    LATENCY = "latency"
    PACKET_LOSS = "packet_loss"
    ROUTE = "route"
    BGP = "bgp"
    LOG = "log"
    CONFIG = "config"
    ASIC = "asic"
    PLATFORM = "platform"
    AVAILABILITY = "availability"


class Significance(str, Enum):
    NORMAL = "normal"
    ELEVATED = "elevated"
    REDUCED = "reduced"
    UNKNOWN = "unknown"
    UNAVAILABLE = "unavailable"


class Evidence(BaseModel):
    """An observation. Must never contain a diagnostic conclusion."""

    evidence_id: str
    timestamp: datetime
    node: str | None = None
    interface: str | None = None
    evidence_type: EvidenceType
    metric: str
    value: Any = None
    unit: str | None = None
    baseline: Any = None
    deviation: float | None = None
    source: str
    tool: str
    raw_reference: str | None = None
    significance: Significance = Significance.UNKNOWN
    confidence: Literal["observed", "parsed", "unavailable"] = "observed"
    investigation_id: str | None = None
    notes: str | None = None
