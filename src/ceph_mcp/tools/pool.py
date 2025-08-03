"""Module for pool tools in Ceph MCP."""

from typing import Annotated
from mcp.types import ToolAnnotations
from pydantic import Field
from ceph_mcp.handlers.pool import PoolHandlers
from ceph_mcp.models.base import MCPResponse
from ceph_mcp.tools.base import ToolModule


class PoolTools(ToolModule):
    """Pool tools for Ceph cluster."""

    def __init__(self, mcp, pool_handlers: PoolHandlers):
        self.pool_handlers = pool_handlers
        super().__init__(mcp, "pool")

    def register_tools(self) -> None:
        """Register pool tools."""

        @self.mcp.tool(
            name="get_pool_summary",
            description="Get cluster pool summary",
            annotations=ToolAnnotations(
                title="Get Pool Summary"
            )
        )
        async def get_pool_summary() -> str:
            """Get summary information about all pools in the Ceph cluster.

            Returns:
                str: Formatted summary of all pools including types, PG status, and health
            """
            response = await self.pool_handlers.handle_request("get_pool_summary", {})
            return self.format_response(response)

        @self.mcp.tool(
            name="get_pool_details",
            description="Get detailed pool information",
            annotations=ToolAnnotations(
                title="Get Pool Details"
            )
        )
        async def get_pool_details(
            pool_name: Annotated[str, Field(
                description="The name of the pool to retrieve details for",
                examples=[
                    "rbd",
                    "cephfs"
                ]
            )]
        ) -> str:
            """Get detailed facts and information about a specific pool.

            Args:
                pool_name (str): Name of the pool to get details for

            Returns:
                str: Detailed pool information including type, replicas, PGs, and applications
            """
            arguments = {"pool_name": pool_name}

            response = await self.pool_handlers.handle_request(
                "get_pool_details", arguments
            )
            return self.format_response(response)

    def format_response(self, response: MCPResponse) -> str:
        """Format response for pool resources as multi-line formatted text."""
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
