"""Module for daemon tools in Ceph MCP."""

from ceph_mcp.handlers.daemon import DaemonHandlers
from ceph_mcp.models.base import MCPResponse
from ceph_mcp.tools.base import ToolModule


class DaemonTools(ToolModule):
    """Daemon tools for Ceph cluster."""

    def __init__(self, mcp, daemon_handlers: DaemonHandlers):
        self.daemon_handlers = daemon_handlers
        super().__init__(mcp, "daemon")

    def register_tools(self) -> None:
        """Register daemon tools."""

        @self.mcp.tool(
            name="get_daemon_summary", description="Get cluster daemon summary"
        )
        async def get_daemon_summary() -> str:
            """Get summary information about all daemons in the Ceph cluster."""
            response = await self.daemon_handlers.handle_request(
                "get_daemon_summary", {}
            )
            return self.format_response(response)

        @self.mcp.tool(name="get_daemon_names", description="Get daemon names by type")
        async def get_daemon_names(daemon_type: str) -> str:
            """Get list of daemon names for a specific daemon type."""
            arguments = {"daemon_type": daemon_type}

            response = await self.daemon_handlers.handle_request(
                "get_daemon_names", arguments
            )
            return self.format_response(response)

        @self.mcp.tool(
            name="get_daemon_details", description="Get detailed daemon information"
        )
        async def get_daemon_details(hostname: str, daemon_name: str) -> str:
            """Get detailed facts and information about a specific daemon."""
            arguments = {"hostname": hostname, "daemon_name": daemon_name}

            response = await self.daemon_handlers.handle_request(
                "get_daemon_details", arguments
            )
            return self.format_response(response)

        @self.mcp.tool(
            name="perform_daemon_action", description="Perform action on daemon"
        )
        async def perform_daemon_action(daemon_name: str, action: str) -> str:
            """Perform an action (start, stop, restart) on a specific daemon."""
            arguments = {"daemon_name": daemon_name, "action": action}

            response = await self.daemon_handlers.handle_request(
                "perform_daemon_action", arguments
            )
            return self.format_response(response)

    def format_response(self, response: MCPResponse) -> str:
        """Format response for daemon resources as multi-line formatted text."""
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
