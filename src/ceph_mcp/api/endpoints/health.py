"""Health-related API endpoints."""

from ceph_mcp.api.base import BaseCephClient, CephAPIError
from ceph_mcp.models.health import (
    ClusterCapacity,
    ClusterHealth,
    HealthCheck,
    HealthCheckSeverity,
    HealthStatus,
)


class HealthClient(BaseCephClient):  # pylint: disable=too-few-public-methods
    """Client for Ceph health-related operations."""

    async def get_cluster_health(self) -> ClusterHealth:
        """Retrieve the overall health status of the Ceph cluster."""
        try:
            response_data = await self._make_request(
                "/api/health/minimal",
                accept_header="application/vnd.ceph.api.v1.0+json",
            )

            cluster_fsid = await self._make_request(
                "/api/health/get_cluster_fsid",
                accept_header="application/vnd.ceph.api.v1.0+json",
            )

            health_data = response_data.get("health", {})

            status_str = health_data.get("status", "HEALTH_ERR")
            try:
                status = HealthStatus(status_str)
            except ValueError:
                self.logger.warning("Unknown health status received", status=status_str)
                status = HealthStatus.ERR

            checks: list[HealthCheck] = self._get_health_checks(
                health_data.get("checks", [])
            )

            return ClusterHealth(
                cluster_fsid=cluster_fsid,
                status=status,
                checks=checks,
                overall_status_description=self._generate_health_description(
                    status, checks
                ),
            )

        except Exception as e:
            self.logger.error("Failed to retrieve cluster health", error=str(e))
            raise CephAPIError(f"Failed to get cluster health: {str(e)}") from e

    def _generate_health_description(
        self, status: HealthStatus, checks: list[HealthCheck]
    ) -> str:
        """Generate a human-readable description of cluster health."""
        if status == HealthStatus.OK:
            return "Cluster is operating normally with no issues detected."
        if status == HealthStatus.WARN:
            # Loop HealthCheck objects to find warnings count
            warnings = [check for check in checks if check.is_warning()]
            return f"Cluster has {len(warnings)} warnings that should be investigated."
        if status == HealthStatus.ERR:
            # Loop HealthCheck objects to find errors count
            errors = [check for check in checks if check.is_critical()]
            return f"Cluster has {len(errors)} errors requiring immediate attention."

        return "Cluster health status is unknown or unrecognized."

    def _get_health_checks(self, checks: list[dict]) -> list[HealthCheck]:
        """Convert raw health checks to HealthCheck models."""
        health_checks = []
        for check in checks:
            detail_messages = []
            for detail in check.get("detail", []):
                detail_messages.append(detail.get("message", ""))
            health_checks.append(
                HealthCheck(
                    type=check.get("type", "unknown"),
                    severity=HealthCheckSeverity(check.get("severity", "unknown")),
                    summary=check.get("summary", {}).get("message", ""),
                    details=", ".join(detail_messages),
                    count=check.get("summary", {}).get("count", 0),
                )
            )
        return health_checks

    async def get_cluster_capacity(self) -> ClusterCapacity:
        """
        Get cluster capacity summary.

        Returns:
            ClusterCapacity: Cluster capacity information

        Raises:
            CephAPIError: If the API request fails
        """
        self.logger.debug("Fetching cluster capacity summary")

        try:
            capacity_data = await self._make_request(
                "/api/health/get_cluster_capacity",
                accept_header="application/vnd.ceph.api.v1.0+json",
            )

            self.logger.debug(
                "Successfully retrieved cluster capacity",
                total_objects=capacity_data.get("total_objects", 0),
            )

            return ClusterCapacity.model_validate(capacity_data)

        except Exception as e:
            self.logger.error("Failed to fetch cluster capacity", error=str(e))
            raise CephAPIError(f"Failed to fetch cluster capacity: {str(e)}") from e
