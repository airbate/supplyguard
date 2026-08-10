"""Auditor agent: decision arbiter and audit writer."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import ClassVar

from supplyguard.models.messages import (
    AuditVerdict,
    RemediationOrder,
    RemediationResult,
    RiskProfile,
)

from .base import Agent


class AuditorAgent(Agent):
    """Makes final verdicts and writes append-only audit logs.

    The Auditor never touches raw untrusted text; it only consumes structured
    evidence chains produced by Analyst.
    """

    name = "Auditor"
    role = "arbiter"
    skills: ClassVar[list[str]] = [
        "policy-check", "human-approval-request", "audit-log-write", "evidence-verify"
    ]

    def handle_risk_profile(self, risk_profile: RiskProfile) -> RemediationOrder:
        """Convert RiskProfile into a RemediationOrder / verdict."""
        action = risk_profile.recommended_action

        if action == "block":
            verdict = AuditVerdict.BLOCK
        elif action in {"remediate", "review"}:
            # Auto-remediation is high-risk; require human approval before merge.
            verdict = AuditVerdict.REQUIRE_HUMAN_REVIEW
        else:
            verdict = AuditVerdict.ALLOW

        strategy = "comment-only"
        if action == "block":
            strategy = "comment-only"
        elif action == "remediate":
            strategy = "bump-version"
        elif action == "review":
            strategy = "comment-only"

        return RemediationOrder(
            session_id=risk_profile.session_id,
            verdict=verdict,
            risk_profile=risk_profile,
            strategy=strategy,
            notes=f"Verdict: {verdict.value}. Reasons: {'; '.join(risk_profile.human_review_reasons) or 'No issues'}",
        )

    def handle_remediation_result(self, result: RemediationResult) -> dict:
        """Seal the audit log after remediation."""
        return {
            "session_id": result.session_id,
            "status": "sealed",
            "regression_detected": result.regression_detected,
            "logs_hash": result.logs_hash,
            "sealed_at": datetime.now(timezone.utc).isoformat(),
        }

    async def handle(self, message: object) -> RemediationOrder | dict | None:
        """Dispatch based on message type."""
        if isinstance(message, RiskProfile):
            return self.handle_risk_profile(message)
        if isinstance(message, RemediationResult):
            return self.handle_remediation_result(message)
        return None
