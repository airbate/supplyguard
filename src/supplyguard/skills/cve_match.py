"""S02: cve-match skill implementation (v1 stub)."""

from __future__ import annotations

from pydantic import BaseModel

from .base import Skill


class CveMatchInput(BaseModel):
    """Input for cve-match."""

    package_name: str
    version: str
    ecosystem: str = "npm"


class CveMatchOutput(BaseModel):
    """Output for cve-match."""

    vulnerable: bool
    max_severity: str | None = None
    cves: list[str] = []
    fixed_versions: list[str] = []
    reasoning: str = ""


class CveMatchSkill(Skill[CveMatchInput, CveMatchOutput]):
    """Match a package version against known vulnerability databases.

    v1 is a deterministic stub that mimics OSV/GHSA responses for demo
    packages. In production this skill will call OSV/GHSA MCP tools.
    """

    name = "cve-match"
    description = "Match package version against CVE / vulnerability databases"

    # Minimal vulnerability database for demos.
    VULNERABLE_VERSIONS: dict[str, dict[str, dict[str, list[str] | str]]] = {
        "lodash": {
            "4.17.4": {
                "severity": "critical",
                "cves": ["CVE-2019-10744", "CVE-2020-8203"],
                "fixed": ["4.17.21"],
            },
            "4.17.15": {
                "severity": "high",
                "cves": ["CVE-2020-8203"],
                "fixed": ["4.17.21"],
            },
        },
        "express": {
            "4.16.0": {
                "severity": "high",
                "cves": ["CVE-2022-24999"],
                "fixed": ["4.17.3"],
            }
        },
    }

    def run(self, input_data: CveMatchInput) -> CveMatchOutput:
        """Return vulnerability matches for the given package version."""
        pkg_db = self.VULNERABLE_VERSIONS.get(input_data.package_name, {})
        match = pkg_db.get(input_data.version)

        if match is None:
            return CveMatchOutput(
                vulnerable=False,
                reasoning=f"No known CVEs for {input_data.package_name}@{input_data.version}.",
            )

        return CveMatchOutput(
            vulnerable=True,
            max_severity=str(match["severity"]),
            cves=list(match["cves"]),
            fixed_versions=list(match["fixed"]),
            reasoning=(
                f"{input_data.package_name}@{input_data.version} matches "
                f"{', '.join(match['cves'])}. Fixed in {', '.join(match['fixed'])}."
            ),
        )
