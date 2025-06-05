"""
Health Domain Handlers

This module contains all MCP request handlers related to cluster health.
"""

from datetime import datetime
from typing import Any

from ceph_mcp.handlers.base import BaseHandler
from ceph_mcp.models.base import MCPResponse


class HealthHandlers(BaseHandler):
    """
    Handlers for health-related MCP operations.

    This class provides all health-related functionality for the MCP server,
    including retrieving health summaries, detailed checks, recommendations.
    """

    def __init__(self) -> None:
        super().__init__(domain="health")

    async def _handle_operation(
        self, operation: str, params: dict[str, Any]
    ) -> MCPResponse:
        """Route health operations to appropriate methods."""
        operation_map = {
            "get_health_summary": self.get_health_summary,
            "get_health_details": self.get_health_details,
            "get_health_recommendations": self.get_health_recommendations,
            "get_cluster_capacity": self.get_cluster_capacity,
        }

        if operation not in operation_map:
            return self.create_error_response(
                message=f"Unknown health operation: {operation}",
                error_code="UNKNOWN_OPERATION",
            )

        return await operation_map[operation](params)

    async def get_health_summary(self, params: dict[str, Any]) -> MCPResponse:
        """
        Get health summary of the Ceph cluster.

        This provides the essential health information that administrators
        need for daily cluster management.
        """
        # Validate required parameters
        self.validate_required_params(params, [])

        # Use global client instead of creating new one
        client = await self.get_global_client()

        # Get raw health data
        health = await client.health.get_cluster_health()

        # Format response data
        summary_data = {
            "executive_summary": health.get_executive_summary(),
            "health_score": health.get_health_score(),
            "status": health.status.value,
            "cluster_fsid": health.cluster_fsid,
            "is_healthy": health.is_healthy(),
            "has_warnings": health.has_warnings(),
            "has_errors": health.has_errors(),
            "description": health.overall_status_description,
            "checks_summary": {
                "total": len(health.checks),
                "critical": len(health.get_critical_checks()),
                "warnings": len(health.get_warning_checks()),
            },
            "recommendations": health.get_recommendations(),
            "timestamp": health.collected_at.isoformat(),
        }

        # Generate appropriate message
        if health.is_healthy():
            message = f"Cluster is healthy (Score: {health.get_health_score()}/100)"
        elif health.has_errors():
            message = f"Cluster has {len(health.get_critical_checks())} critical issue(s) requiring immediate attention"
        else:
            message = f"Cluster has {len(health.get_warning_checks())} warning(s) that should be investigated"

        response = self.create_success_response(data=summary_data, message=message)

        return response

    async def get_health_details(self, params: dict[str, Any]) -> MCPResponse:
        """
        Get detailed health check information for troubleshooting.

        This provides in-depth information about specific health issues
        for detailed diagnosis and resolution.
        """
        # Optional filtering parameters
        severity_filter = self.get_optional_param(params, "severity", None)

        # Use global client instead of creating new one
        client = await self.get_global_client()

        health = await client.health.get_cluster_health()
        # Sort checks by priority
        checks_by_priority = health.get_checks_by_priority()

        # Apply severity filter if specified
        if severity_filter:
            checks_by_priority = [
                check
                for check in checks_by_priority
                if check.severity.value == severity_filter
            ]

        # Format detailed response
        health_details = {
            "overall_status": health.status.value,
            "health_score": health.get_health_score(),
            "description": health.overall_status_description,
            "checks": [
                {
                    "type": check.type,
                    "severity": check.severity.value,
                    "summary": check.summary,
                    "detail": check.details,
                    "count": check.count,
                    "is_critical": check.is_critical(),
                    "is_warning": check.is_warning(),
                    "priority_score": check.get_priority_score(),
                }
                for check in checks_by_priority
            ],
            "check_statistics": {
                "total_checks": len(checks_by_priority),
                "critical_count": len(
                    [check for check in checks_by_priority if check.is_critical()]
                ),
                "warning_count": len(
                    [check for check in checks_by_priority if check.is_warning()]
                ),
                "filtered_by_severity": severity_filter,
            },
            "recommendations": health.get_recommendations(),
            "timestamp": datetime.now().isoformat(),
        }

        # Generate message based on findings
        if not checks_by_priority:
            if severity_filter:
                message = f"No health checks found with severity '{severity_filter}'"
            else:
                message = "Cluster is healthy with no active health checks"
        else:
            critical_count = len(
                [check for check in checks_by_priority if check.is_critical()]
            )
            warning_count = len(
                [check for check in checks_by_priority if check.is_warning()]
            )

            parts = []
            if critical_count > 0:
                parts.append(f"{critical_count} critical issue(s)")
            if warning_count > 0:
                parts.append(f"{warning_count} warning(s)")

            message = f"Found {' and '.join(parts)} requiring attention"

        return self.create_success_response(data=health_details, message=message)

    async def get_health_recommendations(self, params: dict[str, Any]) -> MCPResponse:
        """
        Get specific health recommendations and action items.

        This focuses on providing actionable guidance for cluster management.
        """
        priority_only = self.get_optional_param(params, "priority_only", False)
        max_recommendations = self.get_optional_param(params, "max_recommendations", 10)

        # Use global client instead of creating new one
        client = await self.get_global_client()

        health = await client.health.get_cluster_health()

        # Get comprehensive recommendations
        recommendations = health.get_recommendations()

        # If priority_only is True, filter to most important items
        if priority_only:
            # Focus on critical issues first
            critical_checks = health.get_critical_checks()
            if critical_checks:
                recommendations = [
                    "🚨 Critical issues require immediate attention:",
                    *[f"   - {check.summary}" for check in critical_checks[:3]],
                ]
            else:
                warning_checks = health.get_warning_checks()
                if warning_checks:
                    recommendations = [
                        "⚠️ Address these warnings when possible:",
                        *[f"   - {check.summary}" for check in warning_checks[:3]],
                    ]
                else:
                    recommendations = [
                        "✅ No immediate action required - cluster is healthy"
                    ]

        # Limit number of recommendations
        recommendations = recommendations[:max_recommendations]

        recommendation_data = {
            "recommendations": recommendations,
            "health_score": health.get_health_score(),
            "priority_filter_applied": priority_only,
            "max_items": max_recommendations,
            "total_available": len(health.get_recommendations()),
            "cluster_status": health.status.value,
            "generated_at": datetime.now().isoformat(),
        }

        message = f"Generated {len(recommendations)} health recommendations"
        if priority_only:
            message += " (priority items only)"

        return self.create_success_response(data=recommendation_data, message=message)

    async def get_cluster_capacity(self, params: dict[str, Any]) -> MCPResponse:
        """
        Get cluster capacity summary.

        This provides essential cluster capacity information including
        total objects, capacity in GB, and pool usage statistics.
        """
        # Validate required parameters
        self.validate_required_params(params, [])

        # Use global client instead of creating new one
        client = await self.get_global_client()

        # Get cluster capacity data
        capacity = await client.health.get_cluster_capacity()

        # Format response data
        capacity_data = {
            "cluster_capacity": {
                "total_objects": capacity.total_objects,
                "total_capacity_gb": capacity.get_total_capacity_gb(),
                "used_capacity_gb": capacity.get_used_capacity_gb(),
                "available_capacity_gb": capacity.get_available_capacity_gb(),
                "pool_bytes_used_gb": capacity.get_pool_bytes_used_gb(),
                "usage_percentage": capacity.get_usage_percentage(),
                "average_object_size_kb": capacity.get_average_object_size_kb(),
            },
            "raw_data": {
                "total_avail_bytes": capacity.total_avail_bytes,
                "total_bytes": capacity.total_bytes,
                "total_used_raw_bytes": capacity.total_used_raw_bytes,
                "total_pool_bytes_used": capacity.total_pool_bytes_used,
                "average_object_size": capacity.average_object_size,
            },
            "summary": capacity.get_capacity_summary(),
            "timestamp": datetime.now().isoformat(),
        }

        # Generate descriptive message
        message = f"Cluster capacity: {capacity.get_capacity_summary()} with {capacity.total_objects:,} objects"

        return self.create_success_response(data=capacity_data, message=message)
