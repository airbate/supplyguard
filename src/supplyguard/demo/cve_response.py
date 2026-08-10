"""Demo: zero-day CVE / malicious package response workflow.

Simulates an upstream OSV feed event that discloses a vulnerability in
`lodash@4.17.4`. SupplyGuard scans the repository, evaluates impact,
arbitrates a batch strategy, and generates remediation PRs / comments.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

# Add project root to path for direct script execution
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root / "src"))

from supplyguard.models.messages import (
    AnalysisRequest,
    DependencyChange,
    EventSource,
)
from supplyguard.runtime.local_orchestrator import LocalOrchestrator


async def main() -> None:
    """Run the CVE response demo."""
    orchestrator = LocalOrchestrator()

    # Simulate an OSV feed event: lodash 4.17.4 is vulnerable.
    event = {
        "session_id": "demo-cve-response-001",
        "source": "osv_feed",
        "repo_url": "https://github.com/acme/demo-app",
        "commit_sha": "deadbeef",
        "changes": [
            {
                "package_name": "lodash",
                "old_version": "4.17.4",
                "new_version": None,
                "is_new": False,
                "ecosystem": "npm",
                "context_text": "OSV-2026-XXXX: lodash prototype pollution in 4.17.4",
            }
        ],
    }

    print("=" * 60)  # noqa: T201
    print("SupplyGuard Demo: Zero-day CVE Response")  # noqa: T201
    print("=" * 60)  # noqa: T201

    result = await orchestrator.run_guard(event)

    print("\nWorkflow result:")  # noqa: T201
    print(json.dumps(result, indent=2, default=str))  # noqa: T201

    await orchestrator.close()


if __name__ == "__main__":
    asyncio.run(main())
