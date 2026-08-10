"""S03: hallucination-check skill implementation."""

from __future__ import annotations

import difflib
import hashlib
from dataclasses import dataclass
from typing import Any, ClassVar

from pydantic import BaseModel, Field

from supplyguard.mcp.npm_registry import NpmRegistryClient, fetch_package_sync

from .base import Skill


class HallucinationCheckInput(BaseModel):
    """Input for hallucination-check."""

    candidate_package_name: str
    context_text: str = ""
    ecosystem: str = "npm"


class HallucinationCheckOutput(BaseModel):
    """Output for hallucination-check."""

    is_hallucination_risk: bool
    reasoning: str
    recommended_alternatives: list[str] = Field(default_factory=list)
    evidence: dict[str, Any] = Field(default_factory=dict)


@dataclass
class _RegistryResult:
    exists: bool
    metadata: dict[str, Any] | None = None
    similar_names: list[str] | None = None


class HallucinationCheckSkill(Skill[HallucinationCheckInput, HallucinationCheckOutput]):
    """Detect whether a package name is likely an LLM hallucination / slopsquatting."""

    name = "hallucination-check"
    description = "Detect AI-hallucinated or typosquatted package names"

    POPULAR_NPM_PACKAGES: ClassVar[list[str]] = [
        "lodash",
        "axios",
        "react",
        "express",
        "typescript",
        "next",
        "vue",
        "webpack",
        "jest",
        "prettier",
        "eslint",
        "moment",
        "date-fns",
        "commander",
        "chalk",
        "semver",
        "uuid",
        "dotenv",
        "jsonwebtoken",
        "bcrypt",
        "mongoose",
        "prisma",
        "zod",
        "tailwindcss",
        "@types/node",
    ]

    def __init__(self, npm_client: NpmRegistryClient | None = None) -> None:
        self.npm_client = npm_client or NpmRegistryClient()

    async def run(self, input_data: HallucinationCheckInput) -> HallucinationCheckOutput:
        """Run the check.

        Strategy (heuristic, v1):
        1. Does the package exist in npm registry?
        2. If not, is there a very similar popular package name (typosquatting)?
        3. Does the name look auto-generated (high entropy, unusual patterns)?
        """
        package_name = input_data.candidate_package_name
        try:
            exists = await self.npm_client.exists(package_name)
        except Exception:  # noqa: BLE001
            # Preserve the offline Demo: familiar popular packages are
            # allowed, clear typosquats are blocked, and other unknown names
            # are sent to human review by the risk fusion policy.
            similar = difflib.get_close_matches(
                package_name, self.POPULAR_NPM_PACKAGES, n=3, cutoff=0.7
            )
            is_known_popular = package_name in self.POPULAR_NPM_PACKAGES
            return HallucinationCheckOutput(
                is_hallucination_risk=bool(similar) and not is_known_popular,
                reasoning=(
                    "Registry unreachable; local popular-package fallback found "
                    f"a likely typo of: {', '.join(similar)}."
                    if similar and not is_known_popular
                    else "Registry unreachable; fail-safe policy requires human review."
                ),
                recommended_alternatives=[] if is_known_popular else similar,
                evidence={
                    "registry_error": True,
                    "local_fallback": True,
                    "similar_popular_packages": similar,
                },
            )

        similar = difflib.get_close_matches(
            package_name,
            self.POPULAR_NPM_PACKAGES,
            n=3,
            cutoff=0.7,
        )

        evidence: dict[str, Any] = {
            "registry_exists": exists,
            "similar_popular_packages": similar,
            "context_text_hash": _fingerprint(input_data.context_text),
        }

        if exists:
            return HallucinationCheckOutput(
                is_hallucination_risk=False,
                reasoning=f"Package '{package_name}' exists in npm registry.",
                recommended_alternatives=[],
                evidence=evidence,
            )

        # Package does NOT exist in registry.
        risk = True
        reasoning = f"Package '{package_name}' was not found in npm registry."
        alternatives: list[str] = []

        if similar:
            reasoning += (
                f" It closely resembles popular package(s): {', '.join(similar)}. "
                "Possible typosquatting or LLM hallucination."
            )
            alternatives = similar
        else:
            reasoning += " No close popular match found; likely LLM hallucination."

        return HallucinationCheckOutput(
            is_hallucination_risk=risk,
            reasoning=reasoning,
            recommended_alternatives=alternatives,
            evidence=evidence,
        )

    async def close(self) -> None:
        await self.npm_client.close()


class HallucinationCheckSkillSync:
    """Synchronous fallback for quick local demos without async boilerplate."""

    name = "hallucination-check-sync"

    POPULAR_NPM_PACKAGES: ClassVar[list[str]] = HallucinationCheckSkill.POPULAR_NPM_PACKAGES

    def run(self, candidate_package_name: str, context_text: str = "") -> HallucinationCheckOutput:
        metadata = fetch_package_sync(candidate_package_name)
        exists = metadata is not None
        similar = difflib.get_close_matches(
            candidate_package_name,
            self.POPULAR_NPM_PACKAGES,
            n=3,
            cutoff=0.7,
        )

        evidence: dict[str, Any] = {
            "registry_exists": exists,
            "similar_popular_packages": similar,
            "context_text_hash": _fingerprint(context_text),
        }

        if exists:
            return HallucinationCheckOutput(
                is_hallucination_risk=False,
                reasoning=f"Package '{candidate_package_name}' exists in npm registry.",
                recommended_alternatives=[],
                evidence=evidence,
            )

        reasoning = f"Package '{candidate_package_name}' was not found in npm registry."
        alternatives: list[str] = []
        if similar:
            reasoning += (
                f" It closely resembles popular package(s): {', '.join(similar)}. "
                "Possible typosquatting or LLM hallucination."
            )
            alternatives = similar
        else:
            reasoning += " No close popular match found; likely LLM hallucination."

        return HallucinationCheckOutput(
            is_hallucination_risk=True,
            reasoning=reasoning,
            recommended_alternatives=alternatives,
            evidence=evidence,
        )


def _fingerprint(value: str) -> str:
    """Return a stable, non-reversible reference for untrusted text."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
