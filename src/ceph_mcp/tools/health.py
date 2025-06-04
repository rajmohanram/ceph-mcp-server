"""Module for health tools in Ceph MCP."""

from ceph_mcp.handlers.health import HealthHandlers
from ceph_mcp.models.base import MCPResponse
from ceph_mcp.tools.base import ToolModule


class HealthTools(ToolModule):
    """Health tools for Ceph cluster."""

    def __init__(self, mcp, health_handlers: HealthHandlers):
        self.health_handlers = health_handlers
        super().__init__(mcp, "health")

    def register_tools(self) -> None:
        """Register health tools."""

        @self.mcp.tool(
            name="get_health_summary", description="Get cluster health summary"
        )
        async def get_cluster_health() -> str:
            """Get health summary of the Ceph storage cluster."""
            response = await self.health_handlers.handle_request(
                "get_health_summary", {}
            )
            return self.format_response(response)

        @self.mcp.tool(
            name="get_health_details", description="Get detailed health information"
        )
        async def get_health_details(severity: str | None = None) -> str:
            """Get detailed health check information for troubleshooting."""
            arguments = {"severity": severity}
            arguments = {k: v for k, v in arguments.items() if v is not None}

            response = await self.health_handlers.handle_request(
                "get_health_details", arguments
            )
            return self.format_response(response)

        @self.mcp.tool(
            name="get_health_recommendations", description="Get health recommendations"
        )
        async def get_health_recommendations(
            priority_only: bool = False, max_recommendations: int = 10
        ) -> str:
            """Get specific health recommendations and action items."""
            max_recommendations = max(1, min(50, max_recommendations))

            arguments = {
                "priority_only": priority_only,
                "max_recommendations": max_recommendations,
            }

            response = await self.health_handlers.handle_request(
                "get_health_recommendations", arguments
            )
            return self.format_response(response)

    def format_response(self, response: MCPResponse) -> str:
        """Format response for health resources as multi-line formatted text."""
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
