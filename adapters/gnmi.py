"""gNMI adapter placeholder.

gNMI Get/Set/Capabilities/Subscribe can be added without changing tool names.
MVP investigation uses read-only mock or CLI adapters.
"""

from __future__ import annotations

from adapters.base import CommandResult, NetworkAdapter


class GnmiAdapter(NetworkAdapter):
    name = "gnmi"

    async def execute(self, command: str, node: str, timeout: float | None = None) -> CommandResult:
        return CommandResult(
            status="UNAVAILABLE",
            node=node,
            command=command,
            reason="gNMI is not configured in this environment",
            exit_code=-1,
        )
