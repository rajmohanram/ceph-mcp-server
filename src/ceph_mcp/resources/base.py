"""Base class for resource modules in the MCP system."""

from abc import ABC, abstractmethod

import structlog
from fastmcp import FastMCP

from ceph_mcp.models.base import MCPResponse


class ResourceModule(ABC):
    """Base class for resource modules in the MCP system."""

    def __init__(self, mcp: FastMCP, name: str):
        self.mcp = mcp
        self.name = name
        self.logger = structlog.get_logger(f"resources.{name}")
        # Register resources when created
        self.register_resources()

    @abstractmethod
    def register_resources(self) -> None:
        """Register resources with FastMCP."""

    @abstractmethod
    def format_response(self, response: MCPResponse) -> str:
        """Format response for this module."""
