"""Module for CephFS tools in Ceph MCP."""

from ceph_mcp.handlers.cephfs import CephFSHandlers
from ceph_mcp.models.base import MCPResponse
from ceph_mcp.tools.base import ToolModule


class CephFSTools(ToolModule):
    """CephFS tools for Ceph cluster."""

    def __init__(self, mcp, cephfs_handlers: CephFSHandlers):
        self.cephfs_handlers = cephfs_handlers
        super().__init__(mcp, "cephfs")

    def register_tools(self) -> None:
        """Register CephFS tools."""

        @self.mcp.tool(
            name="get_fs_summary", description="Get CephFS filesystem summary"
        )
        async def get_fs_summary() -> str:
            """Get summary information about all CephFS filesystems in the cluster.

            This tool provides:
            - List of existing filesystem names and their IDs
            - Total count of filesystems
            - Name to ID mappings for easy reference
            """
            response = await self.cephfs_handlers.handle_request("get_fs_summary", {})
            return self.format_response(response)

        @self.mcp.tool(
            name="get_fs_details",
            description="Get detailed information about a specific CephFS filesystem",
        )
        async def get_fs_details(fs_id: int) -> str:
            """Get detailed information about a specific CephFS filesystem.

            This tool provides:
            - Client count
            - Status of each MDS rank (MDS name and state)
            - Filesystem pool statistics:
            * Metadata pool name and usage statistics in GB and percent
            * Data pool name and usage statistics in GB and percent

            Args:
                fs_id: The filesystem ID to get details for
            """
            response = await self.cephfs_handlers.handle_request(
                "get_fs_details", {"fs_id": fs_id}
            )
            return self.format_response(response)

    def format_response(self, response: MCPResponse) -> str:
        """Format response for CephFS resources as multi-line formatted text."""
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
