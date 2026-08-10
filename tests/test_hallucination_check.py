"""Unit tests for hallucination-check skill."""

from __future__ import annotations

from supplyguard.skills.hallucination_check import (
    HallucinationCheckInput,
    HallucinationCheckSkillSync,
)


def test_lodash_is_safe() -> None:
    skill = HallucinationCheckSkillSync()
    result = skill.run("lodash")
    assert result.is_hallucination_risk is False


def test_lodos_is_risk() -> None:
    skill = HallucinationCheckSkillSync()
    result = skill.run("lodos")
    assert result.is_hallucination_risk is True
    assert "lodash" in [a.lower() for a in result.recommended_alternatives]


def test_gibberish_is_risk() -> None:
    skill = HallucinationCheckSkillSync()
    result = skill.run("zxqwmplkjhgfdsa")
    assert result.is_hallucination_risk is True
    assert result.recommended_alternatives == []
