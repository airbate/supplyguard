"""Minimal OSV.dev client used by the cve-match skill.

This is a lightweight equivalent of an MCP tool binding for OSV/GHSA. Like
NpmRegistryClient, it can later be swapped for a real MCP server without
changing the skill's code — the skill only depends on the return shape here.
"""

from __future__ import annotations

from typing import Any, Self

import httpx


class OsvClient:
    """Read-only client for the OSV.dev vulnerability database."""

    def __init__(self, base_url: str = "https://api.osv.dev", timeout: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=timeout)

    async def query_vulns(
        self, package_name: str, version: str, ecosystem: str = "npm"
    ) -> list[dict[str, Any]]:
        """Query vulnerabilities for a package@version.

        Raises:
            httpx.HTTPError: on network failure or non-2xx (caller decides fallback).
        """
        url = f"{self.base_url}/v1/query"
        payload = {
            "package": {"name": package_name, "ecosystem": ecosystem},
            "version": version,
        }
        response = await self._client.post(url, json=payload)
        response.raise_for_status()
        return response.json().get("vulns", [])

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_) -> None:
        await self.close()
