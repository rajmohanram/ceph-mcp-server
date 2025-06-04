"""
Pool Domain Handlers

This module contains all MCP request handlers related to cluster pools.
"""

from datetime import datetime
from typing import Any

from ceph_mcp.api.client import CephClient
from ceph_mcp.handlers.base import BaseHandler
from ceph_mcp.models.base import MCPResponse


class PoolHandlers(BaseHandler):
    """
    Handlers for pool-related MCP operations.

    This class provides all pool-related functionality for the MCP server,
    including retrieving pool summaries and detailed pool information.
    """

    def __init__(self) -> None:
        super().__init__(domain="pool")

    async def _handle_operation(
        self, operation: str, params: dict[str, Any]
    ) -> MCPResponse:
        """Route pool operations to appropriate methods."""
        operation_map = {
            "get_pool_summary": self.get_pool_summary,
            "get_pool_details": self.get_pool_details,
        }

        if operation not in operation_map:
            return self.create_error_response(
                message=f"Unknown pool operation: {operation}",
                error_code="UNKNOWN_OPERATION",
            )

        return await operation_map[operation](params)

    async def get_pool_summary(self, params: dict[str, Any]) -> MCPResponse:
        """
        Get summary information about all pools in the cluster.

        This provides essential pool information that administrators
        need for cluster management overview.
        """
        # Validate required parameters
        self.validate_required_params(params, [])

        async with CephClient() as client:
            # Get pool summary data
            pool_summary = await client.pool.get_pool_summary()

            # Format response data
            summary_data = {
                "cluster_summary": {
                    "total_pools": pool_summary.total_pools,
                    "replicated_pools": pool_summary.replicated_pools,
                    "erasure_pools": pool_summary.erasure_pools,
                    "healthy_pools": pool_summary.healthy_pools,
                    "unhealthy_pools": pool_summary.unhealthy_pools,
                    "total_pgs": pool_summary.total_pgs,
                },
                "pool_types": {
                    pool_type: {
                        "count": type_summary.count,
                        "pool_names": type_summary.pool_names,
                    }
                    for pool_type, type_summary in pool_summary.pool_types.items()
                },
                "pg_status": {
                    state: {
                        "pool_count": state_summary.pool_count,
                        "total_pgs": state_summary.total_pgs,
                    }
                    for state, state_summary in pool_summary.pg_states.items()
                },
                "pool_names": pool_summary.get_pool_names(),
                "unique_applications": pool_summary.get_unique_applications(),
                "average_pool_size": pool_summary.get_average_pool_size(),
                "timestamp": datetime.now().isoformat(),
            }

            # Generate appropriate message
            if pool_summary.unhealthy_pools == 0:
                message = f"All {pool_summary.total_pools} pools are healthy with {pool_summary.total_pgs} total PGs"
            else:
                message = f"Cluster has {pool_summary.total_pools} pools: {pool_summary.healthy_pools} healthy, {pool_summary.unhealthy_pools} with PG issues"

            return self.create_success_response(data=summary_data, message=message)

    async def get_pool_details(self, params: dict[str, Any]) -> MCPResponse:
        """
        Get detailed information about a specific pool.

        This provides comprehensive pool facts for troubleshooting
        and detailed system analysis.
        """
        # Validate required parameters
        self.validate_required_params(params, ["pool_name"])
        pool_name = params["pool_name"]

        async with CephClient() as client:
            # Get detailed pool information
            pool = await client.pool.get_pool_details(pool_name)

            # Format detailed response
            pool_details = {
                "basic_info": {
                    "pool_name": pool.pool_name,
                    "type": pool.type,
                    "crush_rule": pool.crush_rule,
                    "is_replicated": pool.is_replicated(),
                    "is_erasure": pool.is_erasure(),
                },
                "replica_configuration": {
                    "size": pool.size,
                    "min_size": pool.min_size,
                    "replica_info": pool.get_replica_info(),
                },
                "placement_groups": {
                    "pg_num": pool.pg_num,
                    "pg_num_target": pool.pg_num_target,
                    "pg_num_max": pool.options.pg_num_max,
                    "pg_num_min": pool.options.pg_num_min,
                    "pg_placement_num": pool.pg_placement_num,
                    "pg_placement_num_target": pool.pg_placement_num_target,
                },
                "pg_status": {
                    "status_breakdown": pool.pg_status,
                    "total_pgs": pool.get_total_pgs(),
                    "active_pgs": pool.get_active_pgs(),
                    "pg_states": pool.get_pg_states(),
                    "is_healthy": pool.is_healthy(),
                    "pg_efficiency": pool.get_pg_efficiency(),
                },
                "applications": {
                    "application_metadata": pool.application_metadata,
                    "primary_applications": pool.get_primary_applications(),
                    "application_count": len(pool.application_metadata),
                },
                "timestamp": datetime.now().isoformat(),
            }

            # Generate descriptive message
            health_status = "healthy" if pool.is_healthy() else "has PG issues"
            message = f"Pool '{pool_name}' is {pool.type} type with {pool.get_replica_info()} replicas, {pool.get_total_pgs()} PGs and {health_status}"

            return self.create_success_response(data=pool_details, message=message)
