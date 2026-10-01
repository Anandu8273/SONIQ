"""Only registered tools may execute. Arbitrary shell is rejected."""

from __future__ import annotations

from adapters.base import NetworkAdapter
from tools.asic import GetAsicStateTool
from tools.base import DiagnosticTool, RiskLevel, ToolResult, ToolSpec
from tools.bgp import GetBgpStatusTool
from tools.config import GetConfigTool
from tools.interface_errors import GetInterfaceErrorsTool
from tools.interfaces import GetInterfaceStatsTool
from tools.latency import GetLatencyTool
from tools.logs import GetLogsTool
from tools.packet_loss import GetPacketLossTool
from tools.platform import GetPlatformHealthTool
from tools.routing import GetRouteTool


class UnknownToolError(ValueError):
    pass


class ToolNotPermittedError(ValueError):
    pass


class ToolRegistry:
    def __init__(self, adapter: NetworkAdapter, allow_write: bool = False) -> None:
        self.adapter = adapter
        self.allow_write = allow_write
        tools: list[DiagnosticTool] = [
            GetInterfaceStatsTool(adapter),
            GetInterfaceErrorsTool(adapter),
            GetLatencyTool(adapter),
            GetPacketLossTool(adapter),
            GetRouteTool(adapter),
            GetBgpStatusTool(adapter),
            GetLogsTool(adapter),
            GetConfigTool(adapter),
            GetAsicStateTool(adapter),
            GetPlatformHealthTool(adapter),
        ]
        self._tools: dict[str, DiagnosticTool] = {t.spec.name: t for t in tools}

    def get(self, name: str) -> DiagnosticTool:
        if name not in self._tools:
            raise UnknownToolError(f"tool {name!r} is not registered")
        tool = self._tools[name]
        if not tool.spec.read_only and not self.allow_write:
            raise ToolNotPermittedError(f"write tool {name!r} is disabled")
        if tool.spec.risk_level != RiskLevel.READ_ONLY and not self.allow_write:
            raise ToolNotPermittedError(f"tool {name!r} exceeds permitted risk level")
        return tool

    def specs(self) -> list[ToolSpec]:
        return [t.spec for t in self._tools.values()]

    def names(self) -> list[str]:
        return list(self._tools)

    async def execute(self, name: str, arguments: dict) -> ToolResult:
        tool = self.get(name)
        required = tool.spec.input_schema.get("required", [])
        missing = [field for field in required if field not in arguments]
        if missing:
            raise ValueError(f"tool {name} missing required arguments: {missing}")
        return await tool.run(arguments)
