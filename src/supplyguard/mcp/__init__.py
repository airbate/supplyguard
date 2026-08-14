"""MCP-like tool adapters."""

from .npm_registry import NpmRegistryClient
from .osv import OsvClient

__all__ = ["NpmRegistryClient", "OsvClient"]
