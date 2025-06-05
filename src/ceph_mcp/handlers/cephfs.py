"""
CephFS Domain Handlers

This module contains all MCP request handlers related to cluster CephFS filesystems.
"""

from datetime import datetime
from typing import Any

from ceph_mcp.handlers.base import BaseHandler
from ceph_mcp.models.base import MCPResponse


class CephFSHandlers(BaseHandler):
    """
    Handlers for CephFS-related MCP operations.

    This class provides all CephFS-related functionality for the MCP server,
    including retrieving filesystem summaries and detailed filesystem information.
    """

    def __init__(self) -> None:
        super().__init__(domain="cephfs")

    async def _handle_operation(
        self, operation: str, params: dict[str, Any]
    ) -> MCPResponse:
        """Route CephFS operations to appropriate methods."""
        operation_map = {
            "get_fs_summary": self.get_fs_summary,
            "get_fs_details": self.get_fs_details,
        }

        if operation not in operation_map:
            return self.create_error_response(
                message=f"Unknown CephFS operation: {operation}",
                error_code="UNKNOWN_OPERATION",
            )

        return await operation_map[operation](params)

    async def get_fs_summary(self, params: dict[str, Any]) -> MCPResponse:
        """
        Get summary information about all CephFS filesystems in the cluster.

        This provides essential filesystem information that administrators
        need for cluster management overview.
        """
        # Validate required parameters
        self.validate_required_params(params, [])

        # Use global client instead of creating new one
        client = await self.get_global_client()

        # Get CephFS summary data
        fs_summary = await client.cephfs.get_fs_summary()

        # Format response data
        summary_data = {
            "cluster_summary": {
                "total_filesystems": fs_summary.total_filesystems,
                "filesystem_count": len(fs_summary.filesystems),
            },
            "filesystems": [
                {
                    "fs_id": fs.get_fs_id(),
                    "fs_name": fs.get_fs_name(),
                    "display_name": fs.get_display_name(),
                }
                for fs in fs_summary.filesystems
            ],
            "filesystem_names": fs_summary.get_filesystem_names(),
            "filesystem_ids": fs_summary.get_filesystem_ids(),
            "name_id_mapping": fs_summary.get_name_id_mapping(),
            "summary_text": fs_summary.get_summary_text(),
            "timestamp": datetime.now().isoformat(),
        }

        # Generate appropriate message
        if fs_summary.total_filesystems == 0:
            message = "No CephFS filesystems found in the cluster"
        else:
            message = fs_summary.get_summary_text()

        return self.create_success_response(data=summary_data, message=message)

    async def get_fs_details(self, params: dict[str, Any]) -> MCPResponse:
        """
        Get detailed information about a specific CephFS filesystem.

        This provides comprehensive filesystem information including
        client count, MDS ranks status, and pool usage statistics.
        """
        # Validate required parameters
        self.validate_required_params(params, ["fs_id"])

        fs_id = params["fs_id"]

        # Validate fs_id is an integer
        try:
            fs_id = int(fs_id)
        except (ValueError, TypeError):
            return self.create_error_response(
                message=f"Invalid filesystem ID: {fs_id}. Must be an integer.",
                error_code="INVALID_PARAMETER",
            )

        # Use global client
        client = await self.get_global_client()

        # Get CephFS details
        fs_details = await client.cephfs.get_fs_details(fs_id)

        # Format response data
        metadata_pool = fs_details.get_metadata_pool()
        data_pool = fs_details.get_data_pool()

        details_data = {
            "filesystem_info": {
                "fs_id": fs_details.id,
                "fs_name": fs_details.name,
                "client_count": fs_details.client_count,
            },
            "mds_ranks": [
                {
                    "rank": rank.rank,
                    "mds_name": rank.mds,
                    "state": rank.state,
                }
                for rank in fs_details.ranks
            ],
            "pool_statistics": {
                "metadata_pool": (
                    {
                        "name": metadata_pool.pool if metadata_pool else "none",
                        "used_gb": (
                            round(metadata_pool.get_used_gb(), 2)
                            if metadata_pool
                            else 0
                        ),
                        "total_gb": (
                            round(metadata_pool.get_total_gb(), 2)
                            if metadata_pool
                            else 0
                        ),
                        "used_percent": (
                            round(metadata_pool.get_used_percent(), 1)
                            if metadata_pool
                            else 0
                        ),
                    }
                    if metadata_pool
                    else None
                ),
                "data_pool": (
                    {
                        "name": data_pool.pool if data_pool else "none",
                        "used_gb": (
                            round(data_pool.get_used_gb(), 2) if data_pool else 0
                        ),
                        "total_gb": (
                            round(data_pool.get_total_gb(), 2) if data_pool else 0
                        ),
                        "used_percent": (
                            round(data_pool.get_used_percent(), 1) if data_pool else 0
                        ),
                    }
                    if data_pool
                    else None
                ),
            },
            "summary": {
                "active_ranks": len(
                    [r for r in fs_details.ranks if r.state == "active"]
                ),
                "total_ranks": len(fs_details.ranks),
            },
            "timestamp": datetime.now().isoformat(),
        }

        # Generate message
        active_ranks = len([r for r in fs_details.ranks if r.state == "active"])
        message = f"Filesystem '{fs_details.name}' (ID: {fs_details.id}) - {fs_details.client_count} clients, {active_ranks} active MDS ranks"

        return self.create_success_response(data=details_data, message=message)
