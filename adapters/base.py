
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class CommandResult(BaseModel):
    status: str = "OK"
    node: str
    command: str
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    reason: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class NetworkAdapter(ABC):
    """Read-only access to a SONiC node.

    Tools call typed methods. They never send LLM-generated shell.
    Additional transports (gNMI, REST, Redis DBs) can implement this later.
    """

    name: str = "base"

    @abstractmethod
    async def execute(self, command: str, node: str, timeout: float | None = None) -> CommandResult:
        raise NotImplementedError

    async def get_interface_stats(self, node: str, interface: str | None = None) -> dict[str, Any]:
        raise NotImplementedError

    async def get_interface_errors(self, node: str, interface: str | None = None) -> dict[str, Any]:
        raise NotImplementedError

    async def get_latency(self, node: str, destination: str) -> dict[str, Any]:
        raise NotImplementedError

    async def get_packet_loss(self, node: str, destination: str) -> dict[str, Any]:
        raise NotImplementedError

    async def get_routes(self, node: str, destination: str | None = None) -> dict[str, Any]:
        raise NotImplementedError

    async def get_bgp_status(self, node: str) -> dict[str, Any]:
        raise NotImplementedError

    async def get_logs(self, node: str, since_seconds: int = 300, max_lines: int = 50) -> dict[str, Any]:
        raise NotImplementedError

    async def get_config(self, node: str, section: str | None = None) -> dict[str, Any]:
        raise NotImplementedError

    async def get_asic_state(self, node: str) -> dict[str, Any]:
        raise NotImplementedError

    async def get_platform_health(self, node: str) -> dict[str, Any]:
        raise NotImplementedError
