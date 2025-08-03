"""Module for host tools in Ceph MCP."""

from typing import Annotated
from mcp.types import ToolAnnotations
from pydantic import Field
from ceph_mcp.handlers.host import HostHandlers
from ceph_mcp.models.base import MCPResponse
from ceph_mcp.tools.base import ToolModule


class HostTools(ToolModule):
    """Host tools for Ceph cluster."""

    def __init__(self, mcp, host_handlers: HostHandlers):
        self.host_handlers = host_handlers
        super().__init__(mcp, "host")

    def register_tools(self) -> None:
        """Register host tools."""

        @self.mcp.tool(
            name="get_host_summary",
            description="Get cluster host summary",
            annotations=ToolAnnotations(
                title="Get Host Summary"
            )
        )
        async def get_host_summary() -> str:
            """Get summary information about all hosts in the Ceph cluster."""
            response = await self.host_handlers.handle_request(
                "get_host_summary", {}
            )
            return self.format_response(response)

        @self.mcp.tool(
            name="get_host_details",
            description="Get detailed information for a specific host",
            annotations=ToolAnnotations(
                title="Get Host Details"
            )
        )
        async def get_host_details(
            hostname: Annotated[str, Field(
                description="The hostname of the Ceph cluster host"
            )]
        ) -> str:
            """Get detailed facts and information about a specific host."""
            arguments = {"hostname": hostname}

            response = await self.host_handlers.handle_request(
                "get_host_details", arguments
            )
            return self.format_response(response)

    def format_response(self, response: MCPResponse) -> str:
        """Format response for host resources as multi-line formatted text."""
        lines = []
        lines.append(
            f"Operation status: {'success' if response.success else 'failure'}"
        )
        if not response.success and getattr(response, "error_code", None):
            lines.append(f"Error code: {response.error_code}")
        if response.message:
            lines.append(f"Message: {response.message}")
        if response.data:
            lines.append("Data:")
            if isinstance(response.data, dict):
                for k, v in response.data.items():
                    lines.append(f"  {k}: {v}")
            else:
                lines.append(f"  {response.data}")
        if response.timestamp:
            lines.append(f"Collected at: {response.timestamp.isoformat()}")

        formatted_text = "\n".join(lines)
        return formatted_text
