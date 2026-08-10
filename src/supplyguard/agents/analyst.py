"""Analyst agent: read-only risk profiling."""

from __future__ import annotations

from supplyguard.models.messages import AnalysisRequest, Evidence, RiskProfile
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
        self.risk_profile_skill = RiskProfileSkill()

    async def handle(self, message: object) -> RiskProfile | None:
        """Analyze an AnalysisRequest and return a RiskProfile."""
        if not isinstance(message, AnalysisRequest):
            return None

        signals: list[dict] = []
        for change in message.changes:
            # v1 demo: focus on hallucination / slopsquatting signal.
            result = await self.hallucination_skill.run(
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
                    "data": result.model_dump(),
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
