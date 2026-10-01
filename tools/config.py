from __future__ import annotations

from typing import Any

from tools.base import DiagnosticTool, RiskLevel, ToolSpec


class GetConfigTool(DiagnosticTool):
    spec = ToolSpec(
        name="get_config",
        description="Read relevant SONiC configuration. Read-only; never modifies configuration.",
        input_schema={
            "type": "object",
            "properties": {"node": {"type": "string"}, "section": {"type": "string"}},
            "required": ["node"],
        },
        output_schema={"type": "object", "properties": {"config": {"type": "object"}}},
        risk_level=RiskLevel.READ_ONLY,
        read_only=True,
        timeout=15.0,
    )

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return await self.adapter.get_config(arguments["node"], arguments.get("section"))
