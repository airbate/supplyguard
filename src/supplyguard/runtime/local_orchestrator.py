"""Local in-process orchestrator for rapid development and demos.

This is a lightweight stand-in for AgentTeams/HiClaw. It wires Agent instances
together directly, allowing the business logic to be tested before the real
framework integration is complete.
"""

from __future__ import annotations

from typing import Any

from supplyguard.agents.analyst import AnalystAgent
from supplyguard.agents.auditor import AuditorAgent
from supplyguard.agents.remediator import RemediatorAgent
from supplyguard.agents.sentinel import SentinelAgent
from supplyguard.models.messages import (
    AnalysisRequest,
    RemediationOrder,
    RemediationResult,
    RiskProfile,
)
from supplyguard.observability import log_event, span


class LocalOrchestrator:
    """Simple orchestrator that runs the guard workflow in-process."""

    def __init__(self) -> None:
        self.sentinel = SentinelAgent(runtime=self)
        self.analyst = AnalystAgent(runtime=self)
        self.auditor = AuditorAgent(runtime=self)
        self.remediator = RemediatorAgent(runtime=self)

    async def run_guard(self, event: dict[str, Any]) -> dict[str, Any]:
        """Execute the full guard workflow for a single event.

        Flow:
        event -> Sentinel -> AnalysisRequest -> Analyst -> RiskProfile
        -> Auditor -> RemediationOrder -> Remediator -> RemediationResult
        -> Auditor (seal)
        """
        # 1. Sentinel perceives and tags input
        log_event("task.received", session_id=event.get("session_id"), source=event.get("source"))
        with span("sentinel.handle", agent_id="Sentinel"):
            request = await self.sentinel.handle(event)
        if not isinstance(request, AnalysisRequest):
            return {"error": "Sentinel could not parse event"}

        # 2. Analyst produces risk profile
        with span("analyst.handle", agent_id="Analyst", session_id=request.session_id):
            risk_profile = await self.analyst.handle(request)
        if not isinstance(risk_profile, RiskProfile):
            return {"error": "Analyst did not produce a RiskProfile"}

        # 3. Auditor arbitrates
        with span("auditor.arbitrate", agent_id="Auditor", session_id=request.session_id):
            order = self.auditor.handle_risk_profile(risk_profile)
        if not isinstance(order, RemediationOrder):
            return {"error": "Auditor did not produce a RemediationOrder"}

        # 4. Remediator acts (if needed)
        with span("remediator.handle", agent_id="Remediator", session_id=request.session_id):
            result = await self.remediator.handle(order)
        if not isinstance(result, RemediationResult):
            return {"error": "Remediator did not produce a RemediationResult"}

        # 5. Auditor seals audit log
        with span("auditor.seal", agent_id="Auditor", session_id=request.session_id):
            seal = self.auditor.handle_remediation_result(result)
        log_event("task.sealed", session_id=request.session_id, verdict=order.verdict.value)

        return {
            "session_id": request.session_id,
            "source": request.source.value,
            "repo_url": request.repo_url,
            "risk_level": risk_profile.risk_level.value,
            "verdict": order.verdict.value,
            "strategy": order.strategy,
            "remediation": result.artifacts,
            "audit_seal": seal,
        }

    async def close(self) -> None:
        await self.analyst.close()
