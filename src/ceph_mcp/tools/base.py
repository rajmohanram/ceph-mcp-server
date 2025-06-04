"""Base class for tool modules in the MCP system."""

from abc import ABC, abstractmethod
from typing import Any

import structlog
from fastmcp import FastMCP

from ceph_mcp.models.base import MCPResponse


class ToolModule(ABC):
    """Simple base class for tool modules."""

    def __init__(self, mcp: FastMCP, name: str):
        self.mcp = mcp
        self.name = name
        self.logger = structlog.get_logger(f"tools.{name}")

        # Register tools when created
        self.register_tools()

    @abstractmethod
    def register_tools(self) -> None:
        """Register tools with FastMCP."""

    @abstractmethod
    def format_response(self, response: MCPResponse) -> str:
        """Format response for this module."""
