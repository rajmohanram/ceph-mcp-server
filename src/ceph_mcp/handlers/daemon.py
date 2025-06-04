"""
Daemon Domain Handlers

This module contains all MCP request handlers related to cluster daemons.
"""

from datetime import datetime
from typing import Any

from ceph_mcp.api.client import CephClient
from ceph_mcp.handlers.base import BaseHandler
from ceph_mcp.models.base import MCPResponse


class DaemonHandlers(BaseHandler):
    """
    Handlers for daemon-related MCP operations.

    This class provides all daemon-related functionality for the MCP server,
    including retrieving daemon summaries, daemon names by type, and detailed daemon information.
    """

    def __init__(self) -> None:
        super().__init__(domain="daemon")

    async def _handle_operation(
        self, operation: str, params: dict[str, Any]
    ) -> MCPResponse:
        """Route daemon operations to appropriate methods."""
        operation_map = {
            "get_daemon_summary": self.get_daemon_summary,
            "get_daemon_names": self.get_daemon_names,
            "get_daemon_details": self.get_daemon_details,
            "perform_daemon_action": self.perform_daemon_action,
        }

        if operation not in operation_map:
            return self.create_error_response(
                message=f"Unknown daemon operation: {operation}",
                error_code="UNKNOWN_OPERATION",
            )

        return await operation_map[operation](params)

    async def get_daemon_summary(self, params: dict[str, Any]) -> MCPResponse:
        """
        Get summary information about all daemons in the cluster.

        This provides essential daemon information that administrators
        need for cluster management overview.
        """
        # Validate required parameters
        self.validate_required_params(params, [])

        async with CephClient() as client:
            # Get daemon summary data
            daemon_summary = await client.daemon.get_daemon_summary()

            # Format response data
            summary_data = {
                "cluster_summary": {
                    "total_daemons": daemon_summary.total_daemons,
                    "running_daemons": daemon_summary.running_daemons,
                    "stopped_daemons": daemon_summary.stopped_daemons,
                    "daemon_type_count": len(daemon_summary.daemon_types),
                },
                "daemon_types": {
                    daemon_type: {
                        "total_count": type_summary.total_count,
                        "running_count": type_summary.running_count,
                        "stopped_count": type_summary.stopped_count,
                        "daemon_names": type_summary.daemon_names,
                    }
                    for daemon_type, type_summary in daemon_summary.daemon_types.items()
                },
                "all_daemon_names": [
                    daemon.daemon_name for daemon in daemon_summary.daemons
                ],
                "timestamp": datetime.now().isoformat(),
            }

            # Generate appropriate message
            if daemon_summary.stopped_daemons == 0:
                message = f"All {daemon_summary.total_daemons} daemons are running across {len(daemon_summary.daemon_types)} daemon types"
            else:
                message = f"Cluster has {daemon_summary.total_daemons} daemons: {daemon_summary.running_daemons} running, {daemon_summary.stopped_daemons} stopped"

            return self.create_success_response(data=summary_data, message=message)

    async def get_daemon_names(self, params: dict[str, Any]) -> MCPResponse:
        """
        Get list of daemon names for a specific daemon type.

        This provides daemon names filtered by type for targeted management.
        """
        # Validate required parameters
        self.validate_required_params(params, ["daemon_type"])
        daemon_type = params["daemon_type"]

        async with CephClient() as client:
            # Get daemon names by type
            daemon_type_info = await client.daemon.get_daemon_names_by_type(daemon_type)

            # Format response data
            names_data = {
                "daemon_type": daemon_type_info.daemon_type,
                "daemon_names": daemon_type_info.daemon_names,
                "summary": {
                    "total_count": daemon_type_info.total_count,
                    "running_count": daemon_type_info.running_count,
                    "stopped_count": daemon_type_info.stopped_count,
                },
                "timestamp": datetime.now().isoformat(),
            }

            # Generate descriptive message
            if daemon_type_info.total_count == 0:
                message = f"No daemons found for type '{daemon_type}'"
            else:
                message = f"Found {daemon_type_info.total_count} {daemon_type} daemons: {daemon_type_info.running_count} running, {daemon_type_info.stopped_count} stopped"

            return self.create_success_response(data=names_data, message=message)

    async def get_daemon_details(self, params: dict[str, Any]) -> MCPResponse:
        """
        Get detailed information about a specific daemon.

        This provides comprehensive daemon facts for troubleshooting
        and detailed system analysis.
        """
        # Validate required parameters
        self.validate_required_params(params, ["hostname", "daemon_name"])
        hostname = params["hostname"]
        daemon_name = params["daemon_name"]

        async with CephClient() as client:
            # Get detailed daemon information
            daemon = await client.daemon.get_daemon_details(hostname, daemon_name)

            # Format detailed response
            daemon_details = {
                "basic_info": {
                    "daemon_id": daemon.daemon_id,
                    "daemon_type": daemon.daemon_type,
                    "daemon_name": daemon.daemon_name,
                    "hostname": daemon.hostname,
                    "status": daemon.get_status_display(),
                    "status_code": daemon.status,
                },
                "version_info": {
                    "ceph_version": daemon.version,
                    "systemd_unit": daemon.systemd_unit,
                    "started": daemon.started,
                    "started_datetime": (
                        daemon.get_started_datetime().isoformat()
                        if daemon.get_started_datetime()
                        else None
                    ),
                },
                "resource_usage": {
                    "memory_usage_gb": daemon.get_memory_usage_gb(),
                    "memory_request_gb": daemon.get_memory_request_gb(),
                    "cpu_percentage": daemon.cpu_percentage,
                    "cpu_percentage_float": daemon.get_cpu_percentage_float(),
                },
                "timestamp": datetime.now().isoformat(),
            }

            # Generate descriptive message
            uptime_info = ""
            if daemon.get_started_datetime():
                uptime_days = (
                    datetime.now(daemon.get_started_datetime().tzinfo)
                    - daemon.get_started_datetime()
                ).days
                uptime_info = f", running for {uptime_days} days"

            message = f"Daemon '{daemon_name}' on '{hostname}' is {daemon.get_status_display()} using {daemon.get_memory_usage_gb()}GB memory and {daemon.cpu_percentage} CPU{uptime_info}"

            return self.create_success_response(data=daemon_details, message=message)

    async def perform_daemon_action(self, params: dict[str, Any]) -> MCPResponse:
        """
        Perform an action on a specific daemon.

        This allows administrators to start, stop, or restart daemons
        for maintenance and troubleshooting purposes.
        """
        # Validate required parameters
        self.validate_required_params(params, ["daemon_name", "action"])
        daemon_name = params["daemon_name"]
        action = params["action"]

        # Validate action
        valid_actions = ["start", "stop", "restart"]
        if action not in valid_actions:
            return self.create_error_response(
                message=f"Invalid action '{action}'. Valid actions: {', '.join(valid_actions)}",
                error_code="VALIDATION_ERROR",
            )

        async with CephClient() as client:
            # Perform daemon action
            action_result = await client.daemon.perform_daemon_action(
                daemon_name, action
            )

            # Format response data
            action_data = {
                "daemon_info": {
                    "daemon_name": daemon_name,
                    "action_performed": action,
                    "success": action_result["success"],
                },
                "api_response": action_result.get("response", {}),
                "timestamp": datetime.now().isoformat(),
            }

            # Generate descriptive message
            message = f"Successfully {action}ed daemon '{daemon_name}'"

            return self.create_success_response(data=action_data, message=message)
