"""Onion L2/L3: prompt-injection detection for untrusted content.

SupplyGuard's working material — package READMEs, CVE descriptions, PR diffs —
may itself be malicious. A compromised package can embed instructions that try
to steer an Agent into approving it. This detector scans untrusted text for
instruction-override patterns and zero-width/invisible characters before the
text ever reaches an LLM (or is echoed into an evidence summary).

It is deliberately heuristic: the goal is a cheap, deterministic tripwire that
raises the bar and feeds a structured signal to the Auditor — not a full
adversarial classifier.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, Field


class InjectionScanOutput(BaseModel):
    """Result of scanning one piece of untrusted text."""

    suspicious: bool
    matched_patterns: list[str] = Field(default_factory=list)
    zero_width_chars: bool = False
    reasoning: str = ""


# (regex, short label) pairs. Case-insensitive, matched against raw text.
_INJECTION_PATTERNS: list[tuple[str, str]] = [
    (r"ignore\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions|directives|prompt)", "ignore-instructions"),
    (r"disregard\s+(all\s+)?(previous|prior|above)\s+(instructions|directives)", "disregard-instructions"),
    (r"(forget|override)\s+(your|all|the)\s+(previous|prior|system)\s+(instructions|rules)", "override-rules"),
    (r"you\s+are\s+(now|no\s+longer)\s+(a|an|the)\s+\w+", "role-redefinition"),
    (r"system\s+prompt", "system-prompt"),
    (r"developer\s+message", "developer-message"),
    (r"do\s+not\s+(follow|obey|listen)", "disobedience"),
    (r"jailbreak", "jailbreak"),
    (r"as\s+an\s+ai\s+language\s+model", "role-claim"),
]

# Zero-width / invisible / bidi-override characters often used to hide payloads
# from human reviewers while the LLM still parses them. Written as \u escapes so
# the source itself contains no raw control characters.
_ZERO_WIDTH_RE = re.compile(r"[\u200b-\u200f\u202a-\u202e\u2060\ufeff]")


class InjectionDetector:
    """Heuristic prompt-injection scanner (onion L2/L3)."""

    def detect(self, text: str) -> InjectionScanOutput:
        """Return whether `text` looks like an injection attempt."""
        if not text:
            return InjectionScanOutput(suspicious=False, reasoning="empty input")

        matched = [label for pattern, label in _INJECTION_PATTERNS if re.search(pattern, text, re.IGNORECASE)]
        zero_width = bool(_ZERO_WIDTH_RE.search(text))
        suspicious = bool(matched) or zero_width

        reasons: list[str] = []
        if matched:
            reasons.append(f"instruction-override patterns: {', '.join(matched)}")
        if zero_width:
            reasons.append("invisible/zero-width characters detected")

        return InjectionScanOutput(
            suspicious=suspicious,
            matched_patterns=matched,
            zero_width_chars=zero_width,
            reasoning="; ".join(reasons) or "no injection signals",
        )

    def strip_zero_width(self, text: str) -> str:
        """Remove invisible characters before text is stored or echoed."""
        return _ZERO_WIDTH_RE.sub("", text)
