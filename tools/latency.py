from __future__ import annotations

from typing import Any

from tools.base import DiagnosticTool, RiskLevel, ToolSpec


class GetLatencyTool(DiagnosticTool):
    spec = ToolSpec(
        name="get_latency",
        description="Measure latency between a SONiC node and a destination endpoint.",
        input_schema={
            "type": "object",
            "properties": {"node": {"type": "string"}, "destination": {"type": "string"}},
            "required": ["node", "destination"],
        },
        output_schema={"type": "object", "properties": {"avg_ms": {"type": "number"}}},
        risk_level=RiskLevel.READ_ONLY,
        read_only=True,
        timeout=20.0,
    )

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return await self.adapter.get_latency(arguments["node"], arguments["destination"])
