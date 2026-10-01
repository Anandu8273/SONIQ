"""Live SONiC CLI adapter.

Command strings come from configuration. This module does not assume a
specific SONiC version. Phase 1-5 does not execute live commands in tests.
"""

from __future__ import annotations

import asyncio
from typing import Any

from adapters.base import CommandResult, NetworkAdapter
from backend.config import AppConfig, NodeConfig


class SONiCCLIAdapter(NetworkAdapter):
    name = "sonic_cli"

    def __init__(self, config: AppConfig) -> None:
        self.config = config

    async def execute(self, command: str, node: str, timeout: float | None = None) -> CommandResult:
        node_cfg = self._node(node)
        timeout_s = timeout or self.config.tools.timeout_seconds
        if node_cfg.transport == "docker":
            if not node_cfg.container:
                return CommandResult(
                    status="UNAVAILABLE",
                    node=node,
                    command=command,
                    reason="container name is not configured for this node",
                    exit_code=-1,
                )
            return await self._docker_exec(node, node_cfg.container, command, timeout_s)
        if node_cfg.transport == "ssh":
            return CommandResult(
                status="UNAVAILABLE",
                node=node,
                command=command,
                reason="SSH transport is configured but not enabled in this phase",
                exit_code=-1,
            )
        return CommandResult(
            status="UNAVAILABLE",
            node=node,
            command=command,
            reason=f"unsupported transport {node_cfg.transport}",
            exit_code=-1,
        )

    async def _docker_exec(self, node: str, container: str, command: str, timeout_s: float) -> CommandResult:
        proc = await asyncio.create_subprocess_exec(
            "docker",
            "exec",
            container,
            "bash",
            "-lc",
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=timeout_s)
        except TimeoutError:
            proc.kill()
            return CommandResult(status="TIMEOUT", node=node, command=command, reason="tool timeout", exit_code=-1)
        stdout = stdout_b.decode("utf-8", errors="replace")
        stderr = stderr_b.decode("utf-8", errors="replace")
        status = "OK" if proc.returncode == 0 else "UNAVAILABLE"
        return CommandResult(
            status=status,
            node=node,
            command=command,
            stdout=stdout,
            stderr=stderr,
            exit_code=proc.returncode or 0,
            reason=None if proc.returncode == 0 else "command failure",
        )

    def _node(self, node: str) -> NodeConfig:
        if node not in self.config.sonic.nodes:
            raise KeyError(f"unknown node {node}")
        return self.config.sonic.nodes[node]

    async def get_interface_stats(self, node: str, interface: str | None = None) -> dict[str, Any]:
        cmd = self.config.sonic.commands.get("interface_stats", "show interfaces counters")
        result = await self.execute(cmd, node)
        return {"status": result.status, "reason": result.reason, "raw": result.stdout, "node": node, "interface": interface}

    async def get_interface_errors(self, node: str, interface: str | None = None) -> dict[str, Any]:
        cmd = self.config.sonic.commands.get("interface_errors", "show interfaces counters errors")
        result = await self.execute(cmd, node)
        return {"status": result.status, "reason": result.reason, "raw": result.stdout, "node": node, "interface": interface}

    async def get_latency(self, node: str, destination: str) -> dict[str, Any]:
        result = await self.execute(f"ping -c 5 {destination}", node)
        return {"status": result.status, "reason": result.reason, "raw": result.stdout, "node": node, "destination": destination}

    async def get_packet_loss(self, node: str, destination: str) -> dict[str, Any]:
        result = await self.execute(f"ping -c 5 {destination}", node)
        return {"status": result.status, "reason": result.reason, "raw": result.stdout, "node": node, "destination": destination}

    async def get_routes(self, node: str, destination: str | None = None) -> dict[str, Any]:
        cmd = self.config.sonic.commands.get("ip_route", "show ip route")
        result = await self.execute(cmd, node)
        return {"status": result.status, "reason": result.reason, "raw": result.stdout, "node": node, "destination": destination}

    async def get_bgp_status(self, node: str) -> dict[str, Any]:
        cmd = self.config.sonic.commands.get("bgp_summary", "show bgp summary")
        result = await self.execute(cmd, node)
        if result.status != "OK":
            return {"status": "unsupported_or_unavailable", "reason": result.reason or "BGP query failed", "node": node}
        return {"status": "available", "raw": result.stdout, "node": node}

    async def get_logs(self, node: str, since_seconds: int = 300, max_lines: int = 50) -> dict[str, Any]:
        cmd = self.config.sonic.commands.get("logs", "show logging")
        result = await self.execute(cmd, node)
        return {
            "status": result.status,
            "reason": result.reason,
            "raw": result.stdout,
            "node": node,
            "since_seconds": since_seconds,
            "max_lines": max_lines,
        }

    async def get_config(self, node: str, section: str | None = None) -> dict[str, Any]:
        cmd = self.config.sonic.commands.get("running_config", "show runningconfiguration all")
        result = await self.execute(cmd, node)
        return {"status": result.status, "reason": result.reason, "raw": result.stdout, "node": node, "read_only": True}

    async def get_asic_state(self, node: str) -> dict[str, Any]:
        return {"status": "UNAVAILABLE", "reason": "not_available_in_current_environment", "node": node}

    async def get_platform_health(self, node: str) -> dict[str, Any]:
        cmd = self.config.sonic.commands.get("platform_summary", "show platform summary")
        result = await self.execute(cmd, node)
        if result.status != "OK":
            return {
                "status": "UNAVAILABLE",
                "reason": "platform sensors are not exposed in this virtual SONiC environment",
                "node": node,
            }
        return {"status": "OK", "raw": result.stdout, "node": node}
