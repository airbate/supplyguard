"""Unit tests for hallucination-check skill."""

from __future__ import annotations

import asyncio

from supplyguard.skills.hallucination_check import (
    HallucinationCheckInput,
    HallucinationCheckOutput,
    HallucinationCheckSkill,
)


class FakeNpmRegistryClient:
    """Offline registry fixture for deterministic skill tests."""

    def __init__(self, existing_packages: set[str] | None = None) -> None:
        self.existing_packages = existing_packages or set()

    async def exists(self, package_name: str) -> bool:
        return package_name in self.existing_packages

    async def close(self) -> None:
        return None


def run_check(package_name: str) -> HallucinationCheckOutput:
    skill = HallucinationCheckSkill(FakeNpmRegistryClient({"lodash"}))
    return asyncio.run(skill.run(HallucinationCheckInput(candidate_package_name=package_name)))


def test_lodash_is_safe() -> None:
    result = run_check("lodash")
    assert result.is_hallucination_risk is False


def test_lodos_is_risk() -> None:
    result = run_check("lodos")
    assert result.is_hallucination_risk is True
    assert "lodash" in [a.lower() for a in result.recommended_alternatives]


def test_gibberish_is_risk() -> None:
    result = run_check("zxqwmplkjhgfdsa")
    assert result.is_hallucination_risk is True
    assert result.recommended_alternatives == []
