"""
Host Domain Handlers

This module contains all MCP request handlers related to cluster hosts.
"""

from datetime import datetime
from typing import Any

from ceph_mcp.handlers.base import BaseHandler
from ceph_mcp.models.base import MCPResponse


class HostHandlers(BaseHandler):
    """
    Handlers for host-related MCP operations.

    This class provides all host-related functionality for the MCP server,
    including retrieving host summaries and detailed host information.
    """

    def __init__(self) -> None:
        super().__init__(domain="host")

    async def _handle_operation(
        self, operation: str, params: dict[str, Any]
    ) -> MCPResponse:
        """Route host operations to appropriate methods."""
        operation_map = {
            "get_host_summary": self.get_host_summary,
            "get_host_details": self.get_host_details,
        }

        if operation not in operation_map:
            return self.create_error_response(
                message=f"Unknown host operation: {operation}",
                error_code="UNKNOWN_OPERATION",
            )

        return await operation_map[operation](params)

    async def get_host_summary(self, params: dict[str, Any]) -> MCPResponse:
        """
        Get summary information about all hosts in the cluster.

        This provides essential host information that administrators
        need for cluster management overview.
        """
        # Validate required parameters
        self.validate_required_params(params, [])

        # Use global client instead of creating new one
        client = await self.get_global_client()

        # Get host summary data
        host_summary = await client.host.get_host_summary()

        # Format response data
        summary_data = {
            "cluster_summary": {
                "total_hosts": host_summary.total_hosts,
                "online_hosts": host_summary.online_hosts,
                "offline_hosts": host_summary.offline_hosts,
                "online_percentage": (
                    round(
                        (host_summary.online_hosts / host_summary.total_hosts * 100),
                        1,
                    )
                    if host_summary.total_hosts > 0
                    else 0
                ),
            },
            "hosts": [
                {
                    "hostname": host.hostname,
                    "address": host.addr,
                    "status": host.get_status_display(),
                    "services": host.get_service_summary(),
                    "uptime_days": host.get_uptime_days(),
                    "memory_total_gb": host.get_memory_total_gb(),
                    "architecture": host.arch,
                    "labels": host.labels,
                }
                for host in host_summary.hosts
            ],
            "timestamp": datetime.now().isoformat(),
        }

        # Generate appropriate message
        if host_summary.offline_hosts == 0:
            message = f"All {host_summary.total_hosts} hosts are online and operational"
        else:
            message = f"Cluster has {host_summary.total_hosts} hosts: {host_summary.online_hosts} online, {host_summary.offline_hosts} offline"

        return self.create_success_response(data=summary_data, message=message)

    async def get_host_details(self, params: dict[str, Any]) -> MCPResponse:
        """
        Get detailed information about a specific host.

        This provides comprehensive host facts for troubleshooting
        and detailed system analysis.
        """
        # Validate required parameters
        self.validate_required_params(params, ["hostname"])
        hostname = params["hostname"]

        # Use global client instead of creating new one
        client = await self.get_global_client()

        # Get detailed host information
        host = await client.host.get_host_details(hostname)

        # Format detailed response
        host_details = {
            "basic_info": {
                "hostname": host.hostname,
                "fqdn": host.fqdn,
                "shortname": host.shortname,
                "address": host.addr,
                "status": host.get_status_display(),
                "labels": host.labels,
                "uptime_days": host.get_uptime_days(),
            },
            "services": {
                "summary": host.get_service_summary(),
                "instances": [
                    {
                        "type": service.type,
                        "count": service.count,
                    }
                    for service in host.service_instances
                ],
            },
            "hardware": {
                "architecture": host.arch,
                "cpu_model": host.cpu_model,
                "cpu_cores": host.cpu_cores,
                "cpu_count": host.cpu_count,
                "cpu_threads": host.cpu_threads,
            },
            "memory": {
                "total_gb": host.get_memory_total_gb(),
                "available_gb": host.get_memory_available_gb(),
                "free_gb": host.get_memory_free_gb(),
                "used_gb": round(
                    host.get_memory_total_gb() - host.get_memory_free_gb(), 2
                ),
            },
            "system": {
                "operating_system": host.operating_system,
                "kernel_version": host.kernel,
                "system_uptime_seconds": host.system_uptime,
            },
            "timestamp": datetime.now().isoformat(),
        }

        # Generate descriptive message
        memory_usage_pct = (
            round(
                (
                    (host.get_memory_total_gb() - host.get_memory_free_gb())
                    / host.get_memory_total_gb()
                    * 100
                ),
                1,
            )
            if host.get_memory_total_gb() > 0
            else 0
        )

        message = f"Host '{hostname}' is {host.get_status_display()} with {len(host.service_instances)} service types running, {memory_usage_pct}% memory usage"

        return self.create_success_response(data=host_details, message=message)
