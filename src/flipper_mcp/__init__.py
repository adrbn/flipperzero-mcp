"""Flipper MCP - Modular MCP server for Flipper Zero."""

__version__ = "0.1.0"

from importlib import import_module
from typing import Any

__all__ = ["FlipperMCPServer"]


def __getattr__(name: str) -> Any:
    """
    Lazy exports.

    Importing the MCP server requires the optional `mcp` dependency. We keep the
    package importable for core-only utilities (transport/client) without `mcp`.
    """
    if name == "FlipperMCPServer":
        try:
            return import_module(".core.server", __name__).FlipperMCPServer
        except ModuleNotFoundError as e:
            # Provide a clearer error for the common case where `mcp` isn't installed.
            raise ModuleNotFoundError(
                "FlipperMCPServer requires the optional 'mcp' dependency. "
                "Install it (e.g. via this project's requirements) to run the MCP server."
            ) from e
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
