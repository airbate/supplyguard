"""S06: risk-profile skill implementation."""

from __future__ import annotations

import hashlib
from typing import Any

from pydantic import BaseModel, Field

from supplyguard.models.messages import Evidence, RiskLevel, RiskProfile

from .base import Skill


class RiskProfileInput(BaseModel):
    """Input for risk-profile fusion."""

    session_id: str
    entry_mode: str = "guard"  # guard / response
    signals: list[dict[str, Any]] = Field(default_factory=list)


class RiskProfileSkill(Skill[RiskProfileInput, RiskProfile]):
    """Fuse multiple security signals into a structured RiskProfile."""

    name = "risk-profile"
    description = "Fuse multiple security signals into a structured risk profile"

    def run(self, input_data: RiskProfileInput) -> RiskProfile:
        """Simple rule-based fusion engine.

        v1 uses deterministic rules; LLM-based fusion is a v2 enhancement.
        """
        signals = input_data.signals
        evidence_chain: list[Evidence] = []

        hallucination_risk = False
        cve_critical = False
        cve_high = False
        license_violation = False
        maintainer_anomaly = False
        registry_unreachable = False
        injection_detected = False

        for signal in signals:
            skill = signal.get("skill", "unknown")
            data = signal.get("data", {})
            evidence_chain.append(
                Evidence(
                    skill=skill,
                    source=signal.get("source", "internal"),
                    summary=str(data)[:200],
                    confidence=float(signal.get("confidence", 0.5)),
                    raw_fingerprint=hashlib.sha256(
                        repr(sorted(data.items())).encode("utf-8")
                    ).hexdigest()[:16],
                )
            )

            if skill == "hallucination-check":
                if data.get("is_hallucination_risk"):
                    hallucination_risk = True
                # Registry-unreachable is a distinct fail-safe signal, not an
                # alternative to hallucination detection. Report it on its own
                # so an offline typosquat still surfaces the outage (not just
                # the stronger hallucination verdict).
                if data.get("evidence", {}).get("registry_error"):
                    registry_unreachable = True
            elif skill == "cve-match":
                severity = data.get("max_severity", "")
                if severity == "critical":
                    cve_critical = True
                elif severity in {"high", "9.8"}:
                    cve_high = True
            elif skill == "license-check" and not data.get("compatible", True):
                license_violation = True
            elif skill == "maintainer-profile" and data.get("maintainer_change_detected"):
                maintainer_anomaly = True
            elif skill == "injection-scan" and data.get("suspicious"):
                injection_detected = True

        human_review_reasons: list[str] = []

        if injection_detected:
            # A prompt-injection attempt is a meta-attack on the system itself;
            # it outranks every other signal.
            risk_level = RiskLevel.CRITICAL
            recommended_action = "block"
            human_review_reasons.append("Prompt-injection attempt detected in untrusted content.")
        elif hallucination_risk:
            risk_level = RiskLevel.CRITICAL
            recommended_action = "block"
            human_review_reasons.append("Hallucinated or typosquatted package detected.")
        elif cve_critical:
            risk_level = RiskLevel.CRITICAL
            recommended_action = "remediate"
            human_review_reasons.append("Critical CVE detected.")
        elif cve_high or maintainer_anomaly:
            risk_level = RiskLevel.HIGH
            recommended_action = "review"
            human_review_reasons.append("High severity CVE or maintainer anomaly detected.")
        elif license_violation:
            risk_level = RiskLevel.HIGH
            recommended_action = "review"
            human_review_reasons.append("License policy violation detected.")
        elif registry_unreachable:
            risk_level = RiskLevel.HIGH
            recommended_action = "review"
            human_review_reasons.append("Registry unreachable; fail-safe requires human review.")
        else:
            risk_level = RiskLevel.LOW
            recommended_action = "allow"

        return RiskProfile(
            session_id=input_data.session_id,
            risk_level=risk_level,
            recommended_action=recommended_action,
            evidence_chain=evidence_chain,
            human_review_reasons=human_review_reasons,
        )
