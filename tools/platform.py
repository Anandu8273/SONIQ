from __future__ import annotations

from typing import Any

from tools.base import DiagnosticTool, RiskLevel, ToolSpec


class GetPlatformHealthTool(DiagnosticTool):
    spec = ToolSpec(
        name="get_platform_health",
        description="Retrieve platform health (temperature, fans, PSU, transceivers) when available.",
        input_schema={
            "type": "object",
            "properties": {"node": {"type": "string"}},
            "required": ["node"],
        },
        output_schema={"type": "object"},
        risk_level=RiskLevel.READ_ONLY,
        read_only=True,
        timeout=15.0,
    )

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return await self.adapter.get_platform_health(arguments["node"])
