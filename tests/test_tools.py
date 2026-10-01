from __future__ import annotations

import pytest

from adapters.mock_adapter import MockSonicAdapter
from agent.tool_registry import ToolNotPermittedError, ToolRegistry, UnknownToolError
from tools.base import DiagnosticTool, RiskLevel, ToolSpec


@pytest.mark.asyncio
async def test_registered_tools_execute() -> None:
    registry = ToolRegistry(MockSonicAdapter())
    result = await registry.execute("get_latency", {"node": "leaf1", "destination": "leaf2"})
    assert result.success
    assert result.data["avg_ms"] == 35.0


@pytest.mark.asyncio
async def test_unknown_tool_rejected() -> None:
    registry = ToolRegistry(MockSonicAdapter())
    with pytest.raises(UnknownToolError):
        await registry.execute("drop_table", {"node": "leaf1"})


@pytest.mark.asyncio
async def test_missing_arguments_rejected() -> None:
    registry = ToolRegistry(MockSonicAdapter())
    with pytest.raises(ValueError, match="missing required"):
        await registry.execute("get_latency", {"node": "leaf1"})


@pytest.mark.asyncio
async def test_write_tools_disabled() -> None:
    class WriteTool(DiagnosticTool):
        spec = ToolSpec(
            name="shutdown_interface",
            description="would shut an interface",
            input_schema={"type": "object", "properties": {}, "required": []},
            output_schema={"type": "object"},
            risk_level=RiskLevel.HIGH_RISK,
            read_only=False,
        )

        async def execute(self, arguments):
            return {"status": "OK"}

    registry = ToolRegistry(MockSonicAdapter(), allow_write=False)
    registry._tools["shutdown_interface"] = WriteTool(registry.adapter)
    with pytest.raises(ToolNotPermittedError):
        await registry.execute("shutdown_interface", {})


@pytest.mark.asyncio
async def test_timeout_status() -> None:
    adapter = MockSonicAdapter()
    adapter.simulate_timeout = True
    registry = ToolRegistry(adapter)
    result = await registry.execute("get_interface_stats", {"node": "leaf1"})
    assert result.status == "TIMEOUT"
    assert result.success is False


@pytest.mark.asyncio
async def test_unreachable_node() -> None:
    adapter = MockSonicAdapter()
    adapter.unreachable_nodes.add("leaf1")
    registry = ToolRegistry(adapter)
    result = await registry.execute("get_interface_stats", {"node": "leaf1"})
    assert result.status == "UNAVAILABLE"
    assert "unreachable" in (result.error or "").lower()


@pytest.mark.asyncio
async def test_missing_interface() -> None:
    registry = ToolRegistry(MockSonicAdapter())
    result = await registry.execute("get_interface_errors", {"node": "leaf1", "interface": "Ethernet99"})
    assert result.status == "UNAVAILABLE"


@pytest.mark.asyncio
async def test_bgp_unavailable_scenario() -> None:
    registry = ToolRegistry(MockSonicAdapter("bgp_unavailable"))
    result = await registry.execute("get_bgp_status", {"node": "leaf1"})
    assert result.data["status"] == "unsupported_or_unavailable"


@pytest.mark.asyncio
async def test_asic_not_fabricated() -> None:
    registry = ToolRegistry(MockSonicAdapter())
    result = await registry.execute("get_asic_state", {"node": "leaf1"})
    assert result.data["reason"] == "not_available_in_current_environment"
