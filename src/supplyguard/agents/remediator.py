"""Remediator agent: generates PRs / comments and runs sandbox tests."""

from __future__ import annotations

from typing import ClassVar

from supplyguard.models.messages import RemediationOrder, RemediationResult

from .base import Agent


class RemediatorAgent(Agent):
    """Generates remediation artifacts (PRs or comments) and validates them."""

    name = "Remediator"
    role = "remediator"
    skills: ClassVar[list[str]] = [
        "bump-version",
        "swap-dependency",
        "quarantine-package",
        "generate-patch",
        "sandbox-test-run",
    ]

    def _remediate(self, order: RemediationOrder) -> RemediationResult:
        """Execute remediation strategy and return result.

        v1 demo implementation does not perform real git mutations;
        it produces a structured result describing what would happen.
        """
        artifacts: dict = {
            "verdict": order.verdict.value,
            "strategy": order.strategy,
            "notes": order.notes,
            "packages": [
                {
                    "name": ev.skill,
                    "evidence": ev.summary,
                }
                for ev in order.risk_profile.evidence_chain
            ],
        }

        if order.verdict.value == "block":
            artifacts["action_taken"] = "wrote_blocking_comment"
            artifacts["comment_body"] = (
                f"> ⚠️ SupplyGuard blocked this dependency change.\n\n"
                f"{order.notes}\n\n"
                f"Evidence:\n"
                + "\n".join(f"- {ev.skill}: {ev.summary}" for ev in order.risk_profile.evidence_chain)
            )
        elif order.strategy == "bump-version":
            artifacts["action_taken"] = "created_upgrade_pr"
            artifacts["pr_branch"] = f"supplyguard/remediate-{order.session_id[:8]}"
        else:
            artifacts["action_taken"] = "no_action_required"

        return RemediationResult(
            session_id=order.session_id,
            success=True,
            artifacts=artifacts,
            logs_hash="sha256:demo",
            regression_detected=False,
        )

    async def handle(self, message: object) -> RemediationResult | None:
        """Execute a remediation order using the common Agent interface."""
        if isinstance(message, RemediationOrder):
            return self._remediate(message)
        return None
