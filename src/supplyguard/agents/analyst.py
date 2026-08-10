"""Analyst agent: read-only risk profiling."""

from __future__ import annotations

from supplyguard.models.messages import AnalysisRequest, RiskProfile
from supplyguard.skills.cve_match import CveMatchInput, CveMatchSkill
from supplyguard.skills.hallucination_check import (
    HallucinationCheckInput,
    HallucinationCheckSkill,
)
from supplyguard.skills.risk_profile import RiskProfileInput, RiskProfileSkill

from .base import Agent


class AnalystAgent(Agent):
    """Runs read-only skills to produce a structured RiskProfile."""

    name = "Analyst"
    role = "profiler"
    skills = [
        "sbom-build",
        "cve-match",
        "hallucination-check",
        "maintainer-profile",
        "license-check",
        "risk-profile",
        "reachability-scan",
    ]

    def __init__(self, runtime: object | None = None) -> None:
        super().__init__(runtime)
        self.hallucination_skill = HallucinationCheckSkill()
        self.cve_match_skill = CveMatchSkill()
        self.risk_profile_skill = RiskProfileSkill()

    async def handle(self, message: object) -> RiskProfile | None:
        """Analyze an AnalysisRequest and return a RiskProfile."""
        if not isinstance(message, AnalysisRequest):
            return None

        signals: list[dict] = []
        for change in message.changes:
            # Signal 1: hallucination / slopsquatting detection.
            hallucination_result = await self.hallucination_skill.run(
                HallucinationCheckInput(
                    candidate_package_name=change.package_name,
                    context_text=change.context_text,
                    ecosystem=change.ecosystem,
                )
            )
            signals.append(
                {
                    "skill": "hallucination-check",
                    "source": "npm-registry",
                    "confidence": 0.9,
                    "data": hallucination_result.model_dump(),
                }
            )

            # Signal 2: CVE / vulnerability matching.
            # v1 uses a stub database; production will call OSV/GHSA MCP tools.
            version = change.new_version or change.old_version or "unknown"
            cve_result = self.cve_match_skill.run(
                CveMatchInput(
                    package_name=change.package_name,
                    version=version.lstrip("^~>=<") if version != "unknown" else version,
                    ecosystem=change.ecosystem,
                )
            )
            signals.append(
                {
                    "skill": "cve-match",
                    "source": "osv-stub",
                    "confidence": 0.95,
                    "data": cve_result.model_dump(),
                }
            )

        return self.risk_profile_skill.run(
            RiskProfileInput(
                session_id=message.session_id,
                entry_mode="guard" if "pr" in message.source.value else "response",
                signals=signals,
            )
        )

    async def close(self) -> None:
        await self.hallucination_skill.close()
