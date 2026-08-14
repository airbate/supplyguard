"""HiClaw / AgentTeams adapter (skeleton).

The LocalOrchestrator wires the four agents directly for rapid development and
demos. This module defines the boundary for the real AgentTeams runtime, where
Sentinel becomes the Manager and Analyst/Remediator/Auditor run as Workers that
communicate over Matrix rooms.

The mapping mirrors the design doc's §5. It is NOT yet validated against a
live HiClaw hello-world — that remains the single biggest open item before the
semifinal. Until then this adapter is a seam, not a claimed integration.
"""

from __future__ import annotations

from typing import Any, ClassVar, Protocol

from supplyguard.models.messages import SessionState

# The task lifecycle drives both the LocalOrchestrator and (eventually) the
# HiClaw state machine. Order is significant.
LIFECYCLE: list[SessionState] = [
    SessionState.RECEIVED,
    SessionState.ANALYZING,
    SessionState.ARBITRATING,
    SessionState.REMEDIATING,
    SessionState.VERIFYING,
    SessionState.SEALED,
]


class AgentRuntime(Protocol):
    """The minimal surface a real AgentTeams runtime must provide.

    A live HiClaw implementation would dispatch messages into a Matrix room and
    await a Worker's reply; the LocalOrchestrator is an in-process version of
    the same contract.
    """

    async def dispatch(self, agent_id: str, message: dict[str, Any]) -> dict[str, Any]: ...

    async def close(self) -> None: ...


class HiClawAdapter:
    """Maps SupplyGuard's four agents onto HiClaw's Manager + Worker model."""

    # SupplyGuard agent -> HiClaw role.
    ROLE_MAP: ClassVar[dict[str, str]] = {
        "Sentinel": "manager",
        "Analyst": "worker",
        "Remediator": "worker",
        "Auditor": "worker",
    }

    def __init__(self, runtime: AgentRuntime | None = None) -> None:
        self.runtime = runtime

    def manager(self) -> str:
        """The single Manager agent (external entry point)."""
        return "Sentinel"

    def workers(self) -> list[str]:
        """The Worker agents, each with a single responsibility."""
        return ["Analyst", "Remediator", "Auditor"]

    def role_of(self, agent_id: str) -> str:
        return self.ROLE_MAP.get(agent_id, "unknown")

    def lifecycle(self) -> list[str]:
        return [state.value for state in LIFECYCLE]
