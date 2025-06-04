"""
OSD Domain Handlers

This module contains all MCP request handlers related to cluster OSDs.
"""

from datetime import datetime
from typing import Any

from ceph_mcp.handlers.base import BaseHandler
from ceph_mcp.models.base import MCPResponse


class OSDHandlers(BaseHandler):
    """
    Handlers for OSD-related MCP operations.

    This class provides all OSD-related functionality for the MCP server,
    including retrieving OSD summaries, OSD IDs, and detailed OSD information.
    """

    def __init__(self) -> None:
        super().__init__(domain="osd")

    async def _handle_operation(
        self, operation: str, params: dict[str, Any]
    ) -> MCPResponse:
        """Route OSD operations to appropriate methods."""
        operation_map = {
            "get_osd_summary": self.get_osd_summary,
            "get_osd_id": self.get_osd_id,
            "get_osd_details": self.get_osd_details,
            "perform_osd_mark_action": self.perform_osd_mark_action,
        }

        if operation not in operation_map:
            return self.create_error_response(
                message=f"Unknown OSD operation: {operation}",
                error_code="UNKNOWN_OPERATION",
            )

        return await operation_map[operation](params)

    async def get_osd_summary(self, params: dict[str, Any]) -> MCPResponse:
        """
        Get summary information about all OSDs in the cluster.

        This provides essential OSD information that administrators
        need for cluster management overview.
        """
        # Validate required parameters
        self.validate_required_params(params, [])

        # Use global client instead of creating new one
        client = await self.get_global_client()

        # Get OSD summary data
        osd_summary = await client.osd.get_osd_summary()

        # Format response data
        summary_data = {
            "cluster_summary": {
                "total_osds": osd_summary.total_osds,
                "up_osds": osd_summary.up_osds,
                "down_osds": osd_summary.down_osds,
                "in_osds": osd_summary.in_osds,
                "out_osds": osd_summary.out_osds,
                "working_osds": osd_summary.working_osds,
                "up_percentage": (
                    round((osd_summary.up_osds / osd_summary.total_osds * 100), 1)
                    if osd_summary.total_osds > 0
                    else 0
                ),
            },
            "hosts": {
                "unique_hosts": osd_summary.unique_hosts,
                "host_count": len(osd_summary.unique_hosts),
            },
            "device_classes": {
                "unique_classes": osd_summary.device_classes,
                "class_summary": {
                    device_class: {
                        "osd_count": summary.osd_count,
                        "total_pgs": summary.total_pgs,
                        "capacity_gb": summary.get_total_capacity_gb(),
                        "used_gb": summary.get_total_used_gb(),
                        "available_gb": summary.get_total_available_gb(),
                    }
                    for device_class, summary in osd_summary.device_class_summary.items()
                },
            },
            "timestamp": datetime.now().isoformat(),
        }

        # Generate appropriate message
        if osd_summary.down_osds == 0:
            message = f"All {osd_summary.total_osds} OSDs are up and operational across {len(osd_summary.unique_hosts)} hosts"
        else:
            message = f"Cluster has {osd_summary.total_osds} OSDs: {osd_summary.up_osds} up, {osd_summary.down_osds} down"

        return self.create_success_response(data=summary_data, message=message)

    async def get_osd_id(self, params: dict[str, Any]) -> MCPResponse:
        """
        Get list of all OSD IDs and their host assignments.

        This provides OSD ID mapping for cluster management.
        """
        # Validate required parameters
        self.validate_required_params(params, [])

        # Use global client instead of creating new one
        client = await self.get_global_client()

        # Get OSD ID information
        osd_id_info = await client.osd.get_osd_ids()

        # Format response data
        id_data = {
            "osd_mappings": osd_id_info.osd_ids,
            "summary": {
                "total_osds": osd_id_info.total_count,
                "unique_hosts": len(
                    {mapping["hostname"] for mapping in osd_id_info.osd_ids}
                ),
            },
            "timestamp": datetime.now().isoformat(),
        }

        # Generate descriptive message
        host_count = len({mapping["hostname"] for mapping in osd_id_info.osd_ids})
        message = f"Found {osd_id_info.total_count} OSDs distributed across {host_count} hosts"

        return self.create_success_response(data=id_data, message=message)

    async def get_osd_details(self, params: dict[str, Any]) -> MCPResponse:
        """
        Get detailed information about a specific OSD.

        This provides comprehensive OSD facts for troubleshooting
        and detailed system analysis.
        """
        # Validate required parameters
        self.validate_required_params(params, ["osd_id"])
        osd_id = params["osd_id"]

        # Validate osd_id is an integer
        try:
            osd_id = int(osd_id)
        except (ValueError, TypeError):
            return self.create_error_response(
                message=f"OSD ID must be an integer, got: {osd_id}",
                error_code="VALIDATION_ERROR",
            )

        # Use global client instead of creating new one
        client = await self.get_global_client()

        # Get detailed OSD information
        osd = await client.osd.get_osd_details(osd_id)

        # Format detailed response
        osd_details = {
            "basic_info": {
                "osd_id": osd.osd,
                "hostname": osd.get_hostname(),
                "device_class": osd.get_device_class(),
                "weight": osd.weight,
                "operational_status": osd.operational_status,
            },
            "status": {
                "up": osd.is_up(),
                "down": osd.is_down(),
                "in": osd.is_in(),
                "out": osd.is_out(),
                "working": osd.is_working(),
                "status_display": osd.get_status_display(),
            },
            "capacity": {
                "total_kb": osd.osd_stats.kb,
                "used_kb": osd.osd_stats.kb_used,
                "available_kb": osd.osd_stats.kb_avail,
                "total_gb": osd.get_capacity_gb(),
                "used_gb": osd.get_used_gb(),
                "available_gb": osd.get_available_gb(),
                "usage_percentage": osd.get_usage_percentage(),
            },
            "performance": {
                "commit_latency_ms": osd.osd_stats.perf_stat.commit_latency_ms,
                "apply_latency_ms": osd.osd_stats.perf_stat.apply_latency_ms,
                "num_pgs": osd.osd_stats.num_pgs,
            },
            "statistics": {
                "alerts_count": len(osd.osd_stats.alerts),
            },
            "timestamp": datetime.now().isoformat(),
        }

        # Generate descriptive message
        message = f"OSD {osd_id} on '{osd.get_hostname()}' is {osd.get_status_display()} with {osd.get_usage_percentage()}% usage ({osd.get_used_gb()}GB/{osd.get_capacity_gb()}GB)"

        return self.create_success_response(data=osd_details, message=message)

    async def perform_osd_mark_action(self, params: dict[str, Any]) -> MCPResponse:
        """
        Perform a mark action on a specific OSD.

        This allows administrators to mark OSDs as out or noout
        for maintenance and cluster management purposes.
        """
        # Validate required parameters
        self.validate_required_params(params, ["osd_id", "action"])
        osd_id = params["osd_id"]
        action = params["action"]

        # Validate osd_id is an integer
        try:
            osd_id = int(osd_id)
        except (ValueError, TypeError):
            return self.create_error_response(
                message=f"OSD ID must be an integer, got: {osd_id}",
                error_code="VALIDATION_ERROR",
            )

        # Validate action
        valid_actions = ["noout", "out", "in"]
        if action not in valid_actions:
            return self.create_error_response(
                message=f"Invalid action '{action}'. Valid actions: {', '.join(valid_actions)}",
                error_code="VALIDATION_ERROR",
            )

        # Use global client instead of creating new one
        client = await self.get_global_client()

        # Perform OSD mark action
        action_result = await client.osd.perform_osd_mark_action(osd_id, action)

        # Format response data
        action_data = {
            "osd_info": {
                "osd_id": osd_id,
                "action_performed": action,
                "success": action_result["success"],
            },
            "api_response": action_result.get("response", {}),
            "timestamp": datetime.now().isoformat(),
        }

        # Generate descriptive message
        action_description = {
            "out": "marked out (excluded from data placement)",
            "noout": "marked noout (prevented from being automatically marked out)",
            "in": "marked in (included back into data placement)",
        }
        message = f"Successfully {action_description.get(action, action)} OSD {osd_id}"

        return self.create_success_response(data=action_data, message=message)
