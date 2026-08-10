"""Auditor agent: decision arbiter and audit writer."""

from __future__ import annotations

from datetime import datetime, timezone

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
    skills = ["policy-check", "human-approval-request", "audit-log-write", "evidence-verify"]

    def handle_risk_profile(self, risk_profile: RiskProfile) -> RemediationOrder:
        """Convert RiskProfile into a RemediationOrder / verdict."""
        if risk_profile.risk_level.value in {"critical"}:
            verdict = AuditVerdict.BLOCK
        elif risk_profile.risk_level.value in {"high", "medium"}:
            verdict = AuditVerdict.REQUIRE_HUMAN_REVIEW
        else:
            verdict = AuditVerdict.ALLOW

        strategy = "comment-only"
        if risk_profile.recommended_action == "block":
            strategy = "comment-only"
        elif risk_profile.recommended_action == "remediate":
            strategy = "bump-version"
        elif risk_profile.recommended_action == "review":
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
