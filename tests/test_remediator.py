"""Unit tests for the Remediator's action mapping."""

from __future__ import annotations

import asyncio

from supplyguard.agents.remediator import RemediatorAgent
from supplyguard.models.messages import (
    AuditVerdict,
    RemediationOrder,
    RiskLevel,
    RiskProfile,
)


def _order(verdict: AuditVerdict, strategy: str = "comment-only") -> RemediationOrder:
    profile = RiskProfile(
        session_id="test",
        risk_level=RiskLevel.HIGH,
        recommended_action="block",
        evidence_chain=[],
    )
    return RemediationOrder(
        session_id="test",
        verdict=verdict,
        risk_profile=profile,
        strategy=strategy,
    )


def _run(order: RemediationOrder) -> object:
    async def go() -> object:
        return await RemediatorAgent().handle(order)

    return asyncio.run(go())


def test_block_writes_blocking_comment() -> None:
    result = _run(_order(AuditVerdict.BLOCK))
    assert result.artifacts["action_taken"] == "wrote_blocking_comment"
    assert "SupplyGuard blocked" in result.artifacts["comment_body"]


def test_bump_version_creates_upgrade_pr() -> None:
    result = _run(_order(AuditVerdict.REQUIRE_HUMAN_REVIEW, strategy="bump-version"))
    assert result.artifacts["action_taken"] == "created_upgrade_pr"
    assert result.artifacts["pr_branch"].startswith("supplyguard/remediate-")


def test_allow_takes_no_action() -> None:
    result = _run(_order(AuditVerdict.ALLOW))
    assert result.artifacts["action_taken"] == "no_action_required"
