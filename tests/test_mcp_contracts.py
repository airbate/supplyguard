"""Smoke tests for the MCP tool contracts."""

from __future__ import annotations

from supplyguard.mcp.tool_contracts import MCP_TOOLS


def test_every_tool_has_a_valid_contract() -> None:
    assert MCP_TOOLS
    for tool in MCP_TOOLS:
        assert tool["name"]
        assert tool["description"]
        assert tool["inputSchema"]["type"] == "object"
        assert "required" in tool["inputSchema"]
        assert tool["permissions"]
        assert tool["failure_policy"]
