"""Auditor agent: decision arbiter and audit writer."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import ClassVar

from supplyguard.audit import AuditLog
from supplyguard.models.messages import (
    AuditVerdict,
    RemediationOrder,
    RemediationResult,
    RiskProfile,
)

from .base import Agent


class AuditorAgent(Agent):
    """Makes final verdicts and writes append-only, signed audit logs.

    The Auditor never touches raw untrusted text; it only consumes structured
    evidence chains produced by Analyst.
    """

    name = "Auditor"
    role = "arbiter"
    skills: ClassVar[list[str]] = [
        "policy-check", "human-approval-request", "audit-log-write", "evidence-verify"
    ]

    def __init__(self, runtime: object | None = None, signing_key: bytes | None = None) -> None:
        super().__init__(runtime)
        self.audit_log = AuditLog(signing_key)

    def _evidence_hash(self, risk_profile: RiskProfile) -> str:
        fingerprints = "".join(e.raw_fingerprint for e in risk_profile.evidence_chain)
        return hashlib.sha256(fingerprints.encode("utf-8")).hexdigest() if fingerprints else ""

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

        self.audit_log.append(
            session_id=risk_profile.session_id,
            event="verdict",
            verdict=verdict.value,
            evidence_hash=self._evidence_hash(risk_profile),
            agent_actions=[{"agent": "Auditor", "action": "arbitrate"}],
        )

        return RemediationOrder(
            session_id=risk_profile.session_id,
            verdict=verdict,
            risk_profile=risk_profile,
            strategy=strategy,
            notes=f"Verdict: {verdict.value}. Reasons: {'; '.join(risk_profile.human_review_reasons) or 'No issues'}",
        )

    def handle_remediation_result(self, result: RemediationResult) -> dict:
        """Seal the audit log after remediation."""
        self.audit_log.append(
            session_id=result.session_id,
            event="sealed",
            evidence_hash=result.logs_hash,
            agent_actions=[{"agent": "Remediator", "action": result.artifacts.get("action_taken", "")}],
        )
        return {
            "session_id": result.session_id,
            "status": "sealed",
            "regression_detected": result.regression_detected,
            "logs_hash": self.audit_log.head_hash,
            "verified": self.audit_log.verify(),
            "sealed_at": datetime.now(timezone.utc).isoformat(),
        }

    async def handle(self, message: object) -> RemediationOrder | dict | None:
        """Dispatch based on message type."""
        if isinstance(message, RiskProfile):
            return self.handle_risk_profile(message)
        if isinstance(message, RemediationResult):
            return self.handle_remediation_result(message)
        return None
