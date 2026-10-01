from __future__ import annotations

from typing import Any

from tools.base import DiagnosticTool, RiskLevel, ToolSpec


class GetInterfaceErrorsTool(DiagnosticTool):
    spec = ToolSpec(
        name="get_interface_errors",
        description="Retrieve interface error counters (RX/TX/CRC/drops/discards) from a SONiC node.",
        input_schema={
            "type": "object",
            "properties": {"node": {"type": "string"}, "interface": {"type": "string"}},
            "required": ["node"],
        },
        output_schema={"type": "object", "properties": {"interfaces": {"type": "array"}}},
        risk_level=RiskLevel.READ_ONLY,
        read_only=True,
        timeout=15.0,
    )

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return await self.adapter.get_interface_errors(arguments["node"], arguments.get("interface"))
