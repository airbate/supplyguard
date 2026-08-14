"""Unit tests for the cve-match skill (OSV + stub fallback)."""

from __future__ import annotations

import asyncio

from supplyguard.skills.cve_match import CveMatchInput, CveMatchSkill


class FakeOsvClient:
    """Offline OSV fixture with configurable responses."""

    def __init__(self, vulns=None, error: bool = False) -> None:
        self.vulns = vulns if vulns is not None else []
        self.error = error

    async def query_vulns(self, package_name: str, version: str, ecosystem: str = "npm"):
        if self.error:
            raise RuntimeError("offline")
        return self.vulns

    async def close(self) -> None:
        return None


def _run(skill: CveMatchSkill, inp: CveMatchInput) -> object:
    return asyncio.run(skill.run(inp))


def test_osv_vulns_are_parsed() -> None:
    vulns = [
        {
            "aliases": ["CVE-2019-10744"],
            "database_specific": {"severity": "CRITICAL"},
            "affected": [
                {"ranges": [{"events": [{"introduced": "0"}, {"fixed": "4.17.21"}]}]}
            ],
        }
    ]
    out = _run(
        CveMatchSkill(FakeOsvClient(vulns)),
        CveMatchInput(package_name="lodash", version="4.17.4"),
    )
    assert out.vulnerable is True
    assert out.max_severity == "critical"
    assert "CVE-2019-10744" in out.cves
    assert "4.17.21" in out.fixed_versions


def test_osv_empty_result_is_clean() -> None:
    out = _run(
        CveMatchSkill(FakeOsvClient([])),
        CveMatchInput(package_name="lodash", version="4.17.4"),
    )
    assert out.vulnerable is False


def test_osv_failure_falls_back_to_stub() -> None:
    out = _run(
        CveMatchSkill(FakeOsvClient(error=True)),
        CveMatchInput(package_name="lodash", version="4.17.4"),
    )
    assert out.vulnerable is True
    assert out.max_severity == "critical"


def test_moderate_severity_maps_to_medium() -> None:
    vulns = [{"database_specific": {"severity": "MODERATE"}}]
    out = _run(
        CveMatchSkill(FakeOsvClient(vulns)),
        CveMatchInput(package_name="x", version="1.0.0"),
    )
    assert out.max_severity == "medium"
