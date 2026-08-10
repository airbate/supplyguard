"""Sentinel agent: entry point and coordinator."""

from __future__ import annotations

from supplyguard.models.messages import (
    AnalysisRequest,
    DependencyChange,
    EventSource,
)

from .base import Agent


class SentinelAgent(Agent):
    """Listens to external events and routes tasks to Analyst."""

    name = "Sentinel"
    role = "coordinator"
    skills = ["policy-check"]

    async def handle(self, message: object) -> AnalysisRequest | None:
        """Transform external event into an AnalysisRequest.

        This is the "perception layer" of the onion architecture:
        all inputs are tagged as UNTRUSTED and wrapped with boundaries.
        """
        if isinstance(message, AnalysisRequest):
            return message

        # Demo helper: accept raw dicts for convenience.
        if isinstance(message, dict):
            repo = message.get("repo_url", "")
            commit = message.get("commit_sha", "")
            changes_raw = message.get("changes", [])
            source = EventSource(message.get("source", "manual"))
            changes = [DependencyChange(**c) for c in changes_raw]
            return AnalysisRequest(
                session_id=message.get("session_id", "demo-session"),
                source=source,
                repo_url=repo,
                commit_sha=commit,
                changes=changes,
            )

        return None

    def tag_untrusted(self, text: str) -> str:
        """Wrap raw external text with boundary markers."""
        return f"<untrusted_source>\n{text}\n</untrusted_source>"
