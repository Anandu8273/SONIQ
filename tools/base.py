"""Diagnostic tool contract. The LLM may only invoke registered tools."""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from adapters.base import NetworkAdapter

logger = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    READ_ONLY = "READ_ONLY"
    LOW_RISK = "LOW_RISK"
    HIGH_RISK = "HIGH_RISK"


class ToolSpec(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    risk_level: RiskLevel = RiskLevel.READ_ONLY
    read_only: bool = True
    timeout: float = 15.0
    supported_nodes: list[str] | None = None


class ToolResult(BaseModel):
    tool: str
    status: str
    node: str | None = None
    started_at: datetime
    ended_at: datetime
    success: bool
    error: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    raw_reference: str | None = None


class DiagnosticTool(ABC):
    spec: ToolSpec

    def __init__(self, adapter: NetworkAdapter) -> None:
        self.adapter = adapter

    async def run(self, arguments: dict[str, Any]) -> ToolResult:
        started = datetime.now(timezone.utc)
        name = self.spec.name
        node = arguments.get("node")
        logger.info(
            "tool_start",
            extra={"tool": name, "node": node, "arguments": _safe_args(arguments), "start_time": started.isoformat()},
        )
        try:
            data = await asyncio.wait_for(self.execute(arguments), timeout=self.spec.timeout)
            ended = datetime.now(timezone.utc)
            status = str(data.get("status", "OK"))
            success = status in {"OK", "available"}
            error = None if success else str(data.get("reason") or status)
            result = ToolResult(
                tool=name,
                status=status,
                node=node,
                started_at=started,
                ended_at=ended,
                success=success,
                error=error,
                data=data,
            )
        except TimeoutError:
            ended = datetime.now(timezone.utc)
            result = ToolResult(
                tool=name,
                status="TIMEOUT",
                node=node,
                started_at=started,
                ended_at=ended,
                success=False,
                error="tool timeout",
                data={"status": "TIMEOUT", "reason": "tool timeout", "node": node},
            )
        logger.info(
            "tool_end",
            extra={
                "tool": name,
                "node": node,
                "arguments": _safe_args(arguments),
                "start_time": started.isoformat(),
                "end_time": ended.isoformat(),
                "success": result.success,
                "error": result.error,
            },
        )
        return result

    @abstractmethod
    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


def _safe_args(arguments: dict[str, Any]) -> dict[str, Any]:
    blocked = {"password", "api_key", "token", "private_key", "secret"}
    return {k: v for k, v in arguments.items() if k.lower() not in blocked}
