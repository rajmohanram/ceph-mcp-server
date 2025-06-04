"""Module for OSD tools in Ceph MCP."""

from ceph_mcp.handlers.osd import OSDHandlers
from ceph_mcp.models.base import MCPResponse
from ceph_mcp.tools.base import ToolModule


class OSDTools(ToolModule):
    """OSD tools for Ceph cluster."""

    def __init__(self, mcp, osd_handlers: OSDHandlers):
        self.osd_handlers = osd_handlers
        super().__init__(mcp, "osd")

    def register_tools(self) -> None:
        """Register OSD tools."""

        @self.mcp.tool(name="get_osd_summary", description="Get cluster OSD summary")
        async def get_osd_summary() -> str:
            """Get summary information about all OSDs in the Ceph cluster."""
            response = await self.osd_handlers.handle_request("get_osd_summary", {})
            return self.format_response(response)

        @self.mcp.tool(name="get_osd_id", description="Get all OSD IDs and hosts")
        async def get_osd_id() -> str:
            """Get list of all OSD IDs and the hosts they are running on."""
            response = await self.osd_handlers.handle_request("get_osd_id", {})
            return self.format_response(response)

        @self.mcp.tool(
            name="get_osd_details", description="Get detailed OSD information"
        )
        async def get_osd_details(osd_id: int) -> str:
            """Get detailed facts and information about a specific OSD."""
            arguments = {"osd_id": osd_id}

            response = await self.osd_handlers.handle_request(
                "get_osd_details", arguments
            )
            return self.format_response(response)

        @self.mcp.tool(
            name="perform_osd_mark_action", description="Mark OSD in/out status"
        )
        async def perform_osd_mark_action(osd_id: int, action: str) -> str:
            """Perform a mark action (out, noout) on a specific OSD.

            Args:
                osd_id (int): OSD ID number (must be >= 0)
                action (str): Mark action to perform - must be one of: out, noout

            Returns:
                str: Action result and OSD status
            """
            # Add client-side validation since schema enforcement may not be available
            if not isinstance(osd_id, int) or osd_id < 0:
                return f"Error: OSD ID must be a non-negative integer, got: {osd_id}"

            valid_actions = ["noout", "out", "in"]
            if action not in valid_actions:
                return f"Error: Invalid action '{action}'. Valid actions: {', '.join(valid_actions)}"

            arguments = {"osd_id": osd_id, "action": action}

            response = await self.osd_handlers.handle_request(
                "perform_osd_mark_action", arguments
            )
            return self.format_response(response)

    def format_response(self, response: MCPResponse) -> str:
        """Format response for OSD resources as multi-line formatted text."""
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
