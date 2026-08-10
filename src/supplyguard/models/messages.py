"""Schema for inter-agent messages and shared state."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class EventSource(str, Enum):
    """Where a task originates."""

    GITHUB_PR = "github_pr"
    GITLAB_PR = "gitlab_pr"
    OSV_FEED = "osv_feed"
    GHSA_FEED = "ghsa_feed"
    MANUAL = "manual"


class RiskLevel(str, Enum):
    """Aggregate risk assessment."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    SAFE = "safe"


class SessionState(str, Enum):
    """Lifecycle of a SupplyGuard task."""

    RECEIVED = "received"
    ANALYZING = "analyzing"
    ARBITRATING = "arbitrating"
    REMEDIATING = "remediating"
    VERIFYING = "verifying"
    SEALED = "sealed"


class DependencyChange(BaseModel):
    """A single dependency change detected in a PR or event."""

    package_name: str
    old_version: str | None = None
    new_version: str | None = None
    is_new: bool = False
    ecosystem: str = "npm"
    context_text: str = ""


class AnalysisRequest(BaseModel):
    """Sentinel -> Analyst payload."""

    session_id: str
    source: EventSource
    repo_url: str
    commit_sha: str
    changes: list[DependencyChange]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Evidence(BaseModel):
    """A piece of evidence with provenance."""

    skill: str
    source: str
    summary: str
    confidence: float = Field(ge=0.0, le=1.0)
    raw_fingerprint: str


class RiskProfile(BaseModel):
    """Analyst -> Auditor payload."""

    session_id: str
    risk_level: RiskLevel
    recommended_action: str  # block / review / allow / remediate
    evidence_chain: list[Evidence]
    human_review_reasons: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AuditVerdict(str, Enum):
    """Final decision by Auditor."""

    ALLOW = "allow"
    BLOCK = "block"
    REQUIRE_HUMAN_REVIEW = "require_human_review"


class RemediationOrder(BaseModel):
    """Auditor -> Remediator payload."""

    session_id: str
    verdict: AuditVerdict
    risk_profile: RiskProfile
    strategy: str  # bump-version / swap-dependency / comment-only / quarantine
    notes: str = ""


class RemediationResult(BaseModel):
    """Remediator -> Auditor payload."""

    session_id: str
    success: bool
    artifacts: dict[str, Any] = Field(default_factory=dict)
    logs_hash: str = ""
    regression_detected: bool | None = None
    completed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
