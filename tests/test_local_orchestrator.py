"""End-to-end tests for the local guard and response workflows."""

from __future__ import annotations

import asyncio

from supplyguard.runtime.local_orchestrator import LocalOrchestrator
from supplyguard.skills.hallucination_check import HallucinationCheckSkill

from .test_hallucination_check import FakeNpmRegistryClient


def run_workflow(event: dict) -> dict:
    async def run() -> dict:
        orchestrator = LocalOrchestrator()
        orchestrator.analyst.hallucination_skill = HallucinationCheckSkill(
            FakeNpmRegistryClient({"lodash"})
        )
        try:
            return await orchestrator.run_guard(event)
        finally:
            await orchestrator.close()

    return asyncio.run(run())


def test_guard_blocks_a_hallucinated_package() -> None:
    result = run_workflow(
        {
            "session_id": "guard-test",
            "source": "github_pr",
            "repo_url": "https://example.test/acme/demo",
            "commit_sha": "abc123",
            "changes": [
                {
                    "package_name": "lodos",
                    "new_version": "^1.0.0",
                    "is_new": True,
                    "context_text": "import { cloneDeep } from 'lodos'",
                }
            ],
        }
    )

    assert result["risk_level"] == "critical"
    assert result["verdict"] == "block"
    assert result["remediation"]["action_taken"] == "wrote_blocking_comment"
    assert result["audit_seal"]["status"] == "sealed"


def test_response_creates_an_upgrade_pr_for_a_critical_cve() -> None:
    result = run_workflow(
        {
            "session_id": "cve-test",
            "source": "osv_feed",
            "repo_url": "https://example.test/acme/demo",
            "commit_sha": "def456",
            "changes": [
                {
                    "package_name": "lodash",
                    "old_version": "4.17.4",
                    "context_text": "OSV advisory for lodash",
                }
            ],
        }
    )

    assert result["risk_level"] == "critical"
    assert result["verdict"] == "require_human_review"
    assert result["remediation"]["action_taken"] == "created_upgrade_pr"
    assert result["audit_seal"]["status"] == "sealed"
