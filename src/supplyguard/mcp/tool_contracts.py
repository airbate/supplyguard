"""MCP tool contracts.

Declares the JSON Schema for each external tool so the httpx-based clients
(NpmRegistryClient, OsvClient) can later be swapped for a real MCP server
without changing skill code. Each entry mirrors the design doc's §7.1
integration contracts — same tool name, parameter schema, and return shape.
"""

from __future__ import annotations

from typing import Any

# npm registry (Analyst, read-only)
NPM_REGISTRY_TOOL: dict[str, Any] = {
    "name": "npm_registry.fetch_package",
    "description": "Fetch package metadata (versions, maintainers, dist-tags) from the npm registry.",
    "permissions": ["read"],
    "inputSchema": {
        "type": "object",
        "properties": {
            "package_name": {"type": "string", "description": "npm package name (scoped names use @scope/name)."},
        },
        "required": ["package_name"],
    },
    "outputSchema": {
        "type": "object",
        "description": "Package metadata; 404 means the package does not exist.",
    },
    "failure_policy": "registry unreachable -> local cache -> conservative high-risk",
}

# OSV.dev (Analyst, read-only)
OSV_TOOL: dict[str, Any] = {
    "name": "osv.query_vulns",
    "description": "Query OSV.dev for known vulnerabilities in a package version.",
    "permissions": ["read"],
    "inputSchema": {
        "type": "object",
        "properties": {
            "package_name": {"type": "string"},
            "version": {"type": "string"},
            "ecosystem": {"type": "string", "default": "npm"},
        },
        "required": ["package_name", "version"],
    },
    "outputSchema": {
        "type": "object",
        "description": "OSV query result; `vulns` holds advisory entries.",
    },
    "failure_policy": "primary source down -> local vulnerability cache -> conservative high-risk",
}

MCP_TOOLS: list[dict[str, Any]] = [NPM_REGISTRY_TOOL, OSV_TOOL]
