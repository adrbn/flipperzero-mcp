"""Core components for Flipper MCP server."""

from importlib import import_module
from typing import Any

__all__ = ["FlipperMCPServer", "ModuleRegistry", "FlipperClient"]


def __getattr__(name: str) -> Any:
    """
    Lazy exports.

    `FlipperMCPServer` requires the optional `mcp` dependency. Keep core importable
    for transport/client usage without `mcp`.
    """
    if name == "FlipperClient":
        return import_module(".flipper_client", __name__).FlipperClient
    if name == "ModuleRegistry":
        return import_module(".registry", __name__).ModuleRegistry
    if name == "FlipperMCPServer":
        return import_module(".server", __name__).FlipperMCPServer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
