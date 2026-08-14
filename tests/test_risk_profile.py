"""Unit tests for the risk-profile fusion skill."""

from __future__ import annotations

from supplyguard.models.messages import RiskLevel
from supplyguard.skills.risk_profile import RiskProfileInput, RiskProfileSkill


def _run(signals: list[dict]) -> object:
    skill = RiskProfileSkill()
    return skill.run(RiskProfileInput(session_id="test", signals=signals))


def _signal(skill_name: str, data: dict, confidence: float = 0.9) -> dict:
    return {"skill": skill_name, "source": "test", "confidence": confidence, "data": data}


def test_no_signals_allows() -> None:
    result = _run([])
    assert result.risk_level == RiskLevel.LOW
    assert result.recommended_action == "allow"


def test_hallucination_blocks() -> None:
    result = _run([_signal("hallucination-check", {"is_hallucination_risk": True})])
    assert result.risk_level == RiskLevel.CRITICAL
    assert result.recommended_action == "block"


def test_critical_cve_remediates() -> None:
    result = _run([_signal("cve-match", {"max_severity": "critical"})])
    assert result.risk_level == RiskLevel.CRITICAL
    assert result.recommended_action == "remediate"


def test_high_cve_reviews() -> None:
    result = _run([_signal("cve-match", {"max_severity": "high"})])
    assert result.risk_level == RiskLevel.HIGH
    assert result.recommended_action == "review"


def test_license_violation_reviews() -> None:
    result = _run([_signal("license-check", {"compatible": False})])
    assert result.risk_level == RiskLevel.HIGH
    assert result.recommended_action == "review"


def test_maintainer_anomaly_reviews() -> None:
    result = _run([_signal("maintainer-profile", {"maintainer_change_detected": True})])
    assert result.risk_level == RiskLevel.HIGH
    assert result.recommended_action == "review"


def test_registry_unreachable_reviews() -> None:
    result = _run(
        [
            _signal(
                "hallucination-check",
                {"is_hallucination_risk": False, "evidence": {"registry_error": True}},
                confidence=0.5,
            )
        ]
    )
    assert result.risk_level == RiskLevel.HIGH
    assert result.recommended_action == "review"
    assert any("Registry unreachable" in r for r in result.human_review_reasons)


def test_evidence_chain_is_preserved() -> None:
    result = _run([_signal("hallucination-check", {"is_hallucination_risk": True})])
    assert len(result.evidence_chain) == 1
    assert result.evidence_chain[0].skill == "hallucination-check"
