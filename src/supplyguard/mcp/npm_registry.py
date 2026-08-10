"""Minimal npm registry client used by Analyst skills.

This is a lightweight equivalent of an MCP server for npm metadata.
It can later be swapped with a real MCP tool binding without changing skill code.
"""

from __future__ import annotations

import asyncio
from typing import Any, Self

import httpx


class NpmRegistryClient:
    """Read-only client for npm registry metadata."""

    def __init__(self, registry_url: str = "https://registry.npmjs.org") -> None:
        self.registry_url = registry_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=10.0)

    async def fetch_package(self, package_name: str) -> dict[str, Any]:
        """Fetch package metadata from npm registry.

        Raises:
            httpx.HTTPStatusError: if the package does not exist (404).
        """
        encoded = package_name.replace("/", "%2F")
        url = f"{self.registry_url}/{encoded}"
        response = await self._client.get(url)
        response.raise_for_status()
        return response.json()

    async def exists(self, package_name: str) -> bool:
        """Return True if the package exists in the registry."""
        try:
            await self.fetch_package(package_name)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return False
            raise
        return True

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_) -> None:
        await self.close()


# Synchronous helpers for local scripting demos


def fetch_package_sync(package_name: str) -> dict[str, Any] | None:
    """Best-effort synchronous fetch; returns None on 404 or network error."""
    registry_url = "https://registry.npmjs.org"
    encoded = package_name.replace("/", "%2F")
    try:
        response = httpx.get(f"{registry_url}/{encoded}", timeout=10.0)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError:
        return None


if __name__ == "__main__":
    # Quick smoke test
    print(asyncio.run(NpmRegistryClient().exists("lodash")))
    print(fetch_package_sync("lodash") is not None)
