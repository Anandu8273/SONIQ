from __future__ import annotations

from typing import Any

from tools.base import DiagnosticTool, RiskLevel, ToolSpec


class GetLogsTool(DiagnosticTool):
    spec = ToolSpec(
        name="get_logs",
        description="Retrieve a size-limited log summary from a SONiC node.",
        input_schema={
            "type": "object",
            "properties": {
                "node": {"type": "string"},
                "since_seconds": {"type": "integer"},
                "max_lines": {"type": "integer"},
            },
            "required": ["node"],
        },
        output_schema={"type": "object", "properties": {"summary": {"type": "string"}}},
        risk_level=RiskLevel.READ_ONLY,
        read_only=True,
        timeout=15.0,
    )

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return await self.adapter.get_logs(
            arguments["node"],
            since_seconds=int(arguments.get("since_seconds", 300)),
            max_lines=int(arguments.get("max_lines", 50)),
        )
