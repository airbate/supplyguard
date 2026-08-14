"""Unit tests for the Auditor's verdict mapping."""

from __future__ import annotations

from supplyguard.agents.auditor import AuditorAgent
from supplyguard.models.messages import AuditVerdict, RiskLevel, RiskProfile


def _profile(action: str) -> RiskProfile:
    return RiskProfile(
        session_id="test",
        risk_level=RiskLevel.LOW,
        recommended_action=action,
        evidence_chain=[],
    )


def test_block_action_yields_block_verdict() -> None:
    order = AuditorAgent().handle_risk_profile(_profile("block"))
    assert order.verdict == AuditVerdict.BLOCK
    assert order.strategy == "comment-only"


def test_remediate_action_requires_human_review() -> None:
    order = AuditorAgent().handle_risk_profile(_profile("remediate"))
    assert order.verdict == AuditVerdict.REQUIRE_HUMAN_REVIEW
    assert order.strategy == "bump-version"


def test_review_action_requires_human_review() -> None:
    order = AuditorAgent().handle_risk_profile(_profile("review"))
    assert order.verdict == AuditVerdict.REQUIRE_HUMAN_REVIEW
    assert order.strategy == "comment-only"


def test_allow_action_yields_allow_verdict() -> None:
    order = AuditorAgent().handle_risk_profile(_profile("allow"))
    assert order.verdict == AuditVerdict.ALLOW
