"""SSH transport placeholder. Credentials must come from environment, never config committed in git."""

from __future__ import annotations

from adapters.base import CommandResult, NetworkAdapter


class SSHAdapter(NetworkAdapter):
    name = "ssh"

    async def execute(self, command: str, node: str, timeout: float | None = None) -> CommandResult:
        return CommandResult(
            status="UNAVAILABLE",
            node=node,
            command=command,
            reason="SSH adapter is a stub for later phases; no credentials are used in MVP mock mode",
            exit_code=-1,
        )
