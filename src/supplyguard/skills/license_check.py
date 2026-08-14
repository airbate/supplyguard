"""S05: license-check skill implementation.

Pure rule-based license-policy enforcement. No LLM, no network. Unknown
licenses are surfaced for human confirmation rather than auto-blocked, per
the design doc's fail-open-by-default rule for licensing.
"""

from __future__ import annotations

import re
from typing import ClassVar

from pydantic import BaseModel, Field

from .base import Skill


class PackageLicense(BaseModel):
    """A dependency whose license is being checked."""

    name: str
    version: str = ""
    license: str | None = None


class LicensePolicy(BaseModel):
    """An organization's allow/deny license policy."""

    allowed: list[str] = Field(default_factory=list)
    forbidden: list[str] = Field(default_factory=list)
    version: str = "1.0"


class LicenseCheckInput(BaseModel):
    """Input for license-check."""

    packages: list[PackageLicense]
    project_license_policy: LicensePolicy


class LicenseViolation(BaseModel):
    """A single policy conflict."""

    package: str
    license: str
    reason: str


class LicenseCheckOutput(BaseModel):
    """Output for license-check."""

    compatible: bool
    violations: list[LicenseViolation] = Field(default_factory=list)
    unknown_licenses: list[PackageLicense] = Field(default_factory=list)
    policy_version: str


# Common SPDX id aliases -> canonical SPDX id.
_LICENSE_ALIASES: ClassVar[dict[str, str]] = {
    "apache 2.0": "Apache-2.0",
    "apache-2": "Apache-2.0",
    "apache2": "Apache-2.0",
    "apache license 2.0": "Apache-2.0",
    "apache-2.0": "Apache-2.0",
    "bsd": "BSD-3-Clause",
    "bsd-2-clause": "BSD-2-Clause",
    "bsd-3-clause": "BSD-3-Clause",
    "gpl": "GPL-3.0",
    "gpl-2.0": "GPL-2.0",
    "gpl-3.0": "GPL-3.0",
    "gplv2": "GPL-2.0",
    "gplv3": "GPL-3.0",
    "agpl-3.0": "AGPL-3.0",
    "lgpl-2.1": "LGPL-2.1",
    "lgpl-3.0": "LGPL-3.0",
    "mit": "MIT",
    "isc": "ISC",
    "unlicense": "Unlicense",
    "cc0-1.0": "CC0-1.0",
    "mpl-2.0": "MPL-2.0",
    "mozilla public license 2.0": "MPL-2.0",
}


def normalize_license(raw: str | None) -> str | None:
    """Normalize a raw license string to a canonical SPDX id (best effort)."""
    if not raw:
        return None
    # Take the first arm of an SPDX expression ("MIT OR Apache-2.0" -> "MIT").
    s = re.split(r"\s+(?:OR|AND)\s+", raw.strip(), flags=re.IGNORECASE)[0]
    s = s.strip("() ").strip()
    key = s.lower()
    return _LICENSE_ALIASES.get(key, s)


class LicenseCheckSkill(Skill[LicenseCheckInput, LicenseCheckOutput]):
    """Detect license-policy conflicts for a list of packages."""

    name = "license-check"
    description = "Detect license conflicts against an organization policy"

    def run(self, input_data: LicenseCheckInput) -> LicenseCheckOutput:
        """Evaluate each package license against the policy."""
        policy = input_data.project_license_policy
        allowed = {normalize_license(x) for x in policy.allowed}
        forbidden = {normalize_license(x) for x in policy.forbidden}

        violations: list[LicenseViolation] = []
        unknown: list[PackageLicense] = []

        for pkg in input_data.packages:
            normalized = normalize_license(pkg.license)
            if normalized is None:
                unknown.append(pkg)
                continue
            if normalized in forbidden:
                violations.append(
                    LicenseViolation(
                        package=pkg.name,
                        license=pkg.license or "",
                        reason=f"License '{pkg.license}' is forbidden by policy.",
                    )
                )
            elif normalized not in allowed:
                # Not explicitly allowed and not forbidden -> needs human eyes.
                unknown.append(pkg)

        return LicenseCheckOutput(
            compatible=not violations,
            violations=violations,
            unknown_licenses=unknown,
            policy_version=policy.version,
        )
