"""Module for health resources in Ceph MCP."""

from ceph_mcp.handlers.health import HealthHandlers
from ceph_mcp.models.base import MCPResponse
from ceph_mcp.resources.base import ResourceModule


class HealthResources(ResourceModule):
    """Health resources for Ceph cluster."""

    def __init__(self, mcp, health_handlers: HealthHandlers):
        self.health_handlers = health_handlers
        super().__init__(mcp, "health")

    def register_resources(self) -> None:
        """Register health resources."""

        @self.mcp.resource(
            uri="ceph://health/summary",
            name="HealthSummary",
            description="Provides a summary of the cluster's health status.",
            tags={"health", "summary"},
        )
        async def get_health_summary() -> str:
            """Get health summary of the Ceph storage cluster."""
            response = await self.health_handlers.handle_request(
                "get_health_summary", {}
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
