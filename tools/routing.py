from __future__ import annotations

from typing import Any

from tools.base import DiagnosticTool, RiskLevel, ToolSpec


class GetRouteTool(DiagnosticTool):
    spec = ToolSpec(
        name="get_route",
        description="Inspect routing information on a SONiC node.",
        input_schema={
            "type": "object",
            "properties": {"node": {"type": "string"}, "destination": {"type": "string"}},
            "required": ["node"],
        },
        output_schema={"type": "object", "properties": {"routes": {"type": "array"}}},
        risk_level=RiskLevel.READ_ONLY,
        read_only=True,
        timeout=15.0,
    )

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return await self.adapter.get_routes(arguments["node"], arguments.get("destination"))
