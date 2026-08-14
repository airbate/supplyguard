"""S02: cve-match skill implementation.

Queries the OSV.dev vulnerability database for a package@version and falls
back to a small local stub database when the network is unavailable. The
OSV/GHSA data source keeps the guard/response modes working on real advisories
rather than a hardcoded demo table.
"""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel

from supplyguard.mcp.osv import OsvClient

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


_SEVERITY_ORDER: dict[str, int] = {"low": 1, "medium": 2, "high": 3, "critical": 4}


def _extract_cves(vuln: dict[str, Any]) -> list[str]:
    return [a for a in vuln.get("aliases", []) if isinstance(a, str) and a.startswith("CVE-")]


def _extract_fixed_versions(vuln: dict[str, Any]) -> list[str]:
    fixed: set[str] = set()
    for affected in vuln.get("affected", []):
        for rng in affected.get("ranges", []):
            for event in rng.get("events", []):
                if isinstance(event, dict) and "fixed" in event:
                    fixed.add(str(event["fixed"]))
    return sorted(fixed)


def _extract_severity(vuln: dict[str, Any]) -> str:
    """Extract a severity label, preferring GHSA's textual rating.

    GHSA advisories carry `database_specific.severity` (LOW/MODERATE/HIGH/
    CRITICAL), which is the most reliable signal in the npm ecosystem. When
    absent we fall back to a conservative "high" rather than mis-parse a CVSS
    vector.
    """
    sev = (vuln.get("database_specific") or {}).get("severity")
    if sev:
        sev = str(sev).lower()
        return "medium" if sev == "moderate" else sev
    return "high"


class CveMatchSkill(Skill[CveMatchInput, CveMatchOutput]):
    """Match a package version against OSV/GHSA (with offline stub fallback)."""

    name = "cve-match"
    description = "Match package version against CVE / vulnerability databases"

    # Minimal offline fallback database for demos and CI.
    VULNERABLE_VERSIONS: ClassVar[dict[str, dict[str, dict[str, list[str] | str]]]] = {
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

    def __init__(self, osv_client: OsvClient | None = None) -> None:
        self.osv_client = osv_client or OsvClient()

    async def run(self, input_data: CveMatchInput) -> CveMatchOutput:
        """Query OSV first, then degrade to the local stub on network failure.

        An empty OSV result is a *real* "no known vulnerabilities" answer, not
        a reason to fall back to the stub — otherwise a clean package that also
        exists in the demo stub would be falsely flagged.
        """
        try:
            vulns = await self.osv_client.query_vulns(
                input_data.package_name, input_data.version, input_data.ecosystem
            )
        except Exception:  # noqa: BLE001 — network failure degrades to stub
            return self._from_stub(input_data)

        if vulns:
            return self._from_osv(input_data, vulns)
        return CveMatchOutput(
            vulnerable=False,
            reasoning=f"No known CVEs for {input_data.package_name}@{input_data.version}.",
        )

    def _from_osv(self, input_data: CveMatchInput, vulns: list[dict[str, Any]]) -> CveMatchOutput:
        severities = [_extract_severity(v) for v in vulns]
        max_severity = max(severities, key=lambda s: _SEVERITY_ORDER.get(s, 0))
        cves: list[str] = []
        fixed: set[str] = set()
        for v in vulns:
            cves.extend(_extract_cves(v))
            fixed.update(_extract_fixed_versions(v))

        return CveMatchOutput(
            vulnerable=True,
            max_severity=max_severity,
            cves=sorted(set(cves)),
            fixed_versions=sorted(fixed),
            reasoning=(
                f"{input_data.package_name}@{input_data.version} matches "
                f"{len(vulns)} OSV advisorie(s); max severity {max_severity}."
            ),
        )

    def _from_stub(self, input_data: CveMatchInput) -> CveMatchOutput:
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

    async def close(self) -> None:
        await self.osv_client.close()
