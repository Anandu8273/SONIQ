from __future__ import annotations

from typing import Any

from tools.base import DiagnosticTool, RiskLevel, ToolSpec


class GetBgpStatusTool(DiagnosticTool):
    spec = ToolSpec(
        name="get_bgp_status",
        description="Retrieve BGP neighbor session state if BGP is configured.",
        input_schema={
            "type": "object",
            "properties": {"node": {"type": "string"}},
            "required": ["node"],
        },
        output_schema={"type": "object", "properties": {"neighbors": {"type": "array"}}},
        risk_level=RiskLevel.READ_ONLY,
        read_only=True,
        timeout=15.0,
    )

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return await self.adapter.get_bgp_status(arguments["node"])
