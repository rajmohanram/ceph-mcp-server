"""
Health Domain Models

This module contains all models related to Ceph cluster health,
extracted from the original ceph_models.py and enhanced.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from ceph_mcp.models.base import BaseComponentInfo


class HealthStatus(str, Enum):
    """
    Standardized health status values that Ceph uses.

    Using an enum ensures we only work with valid status values and makes
    it easier to handle status-specific logic throughout the application.
    """

    OK = "HEALTH_OK"
    WARN = "HEALTH_WARN"
    ERR = "HEALTH_ERR"


class HealthCheckSeverity(str, Enum):
    """Severity levels for individual health checks."""

    INFO = "HEALTH_INFO"
    WARN = "HEALTH_WARN"
    ERR = "HEALTH_ERR"


class HealthCheck(BaseModel):
    """
    Individual health check information.

    Represents a single health check with its details and recommendations.
    """

    type: str = Field(..., description="Health check type")
    severity: HealthCheckSeverity = Field(description="Severity level of this check")
    summary: str = Field(description="Human-readable summary of the issue")
    details: str = Field(default="", description="Detailed information about the issue")
    count: int = Field(default=0, description="Number of affected components")

    def is_critical(self) -> bool:
        """
        Check if this health check represents a critical issue.
        """
        return self.severity == HealthCheckSeverity.ERR

    def is_warning(self) -> bool:
        """
        Check if this health check represents a warning.
        """
        return self.severity == HealthCheckSeverity.WARN

    def get_priority_score(self) -> int:
        """
        Get a numeric priority score for sorting (higher = more urgent).
        """
        priority_map = {
            HealthCheckSeverity.ERR: 100,
            HealthCheckSeverity.WARN: 50,
            HealthCheckSeverity.INFO: 10,
        }
        return priority_map.get(self.severity, 0)


class ClusterHealth(BaseComponentInfo):
    """
    Represents the overall health status of a Ceph cluster.
    """

    name: str = Field(
        default="cluster_health", description="Identifier for the Component"
    )
    status: HealthStatus = Field(description="Overall cluster health status")
    checks: list[HealthCheck] = Field(
        default_factory=list, description="Individual health checks"
    )
    overall_status_description: str | None = Field(
        None, description="Detailed explanation of current status"
    )
    collected_at: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when metrics were collected",
    )

    def is_healthy(self) -> bool:
        """
        Convenience method to check if cluster is in good health.
        """
        return self.status == HealthStatus.OK

    def has_warnings(self) -> bool:
        """
        Check if cluster has warnings that need attention.
        """
        return self.status == HealthStatus.WARN or any(
            check.is_warning() for check in self.checks
        )

    def has_errors(self) -> bool:
        """
        Check if cluster has errors requiring immediate attention.
        """
        return self.status == HealthStatus.ERR or any(
            check.is_critical() for check in self.checks
        )

    def get_critical_checks(self) -> list[HealthCheck]:
        """Get all critical health checks."""
        return [check for check in self.checks if check.is_critical()]

    def get_warning_checks(self) -> list[HealthCheck]:
        """Get all warning health checks."""
        return [check for check in self.checks if check.is_warning()]

    def get_checks_by_priority(self) -> list[HealthCheck]:
        """Get health checks sorted by priority (most urgent first)."""
        return sorted(self.checks, key=lambda x: x.get_priority_score(), reverse=True)

    def get_health_score(self) -> int:
        """
        Get a numeric health score (0-100, where 100 is perfect health).

        This provides a single number that can be used for monitoring
        and trend analysis.
        """
        if self.status == HealthStatus.OK:
            return 100

        # Deduct points based on check severity
        score = 100
        for check in self.checks:
            if check.is_critical():
                score -= 30  # Critical issues heavily impact score
            elif check.is_warning():
                score -= 10  # Warnings have moderate impact

        return max(0, score)

    def get_recommendations(self) -> list[str]:
        """Get actionable recommendations based on current health status."""
        recommendations = []

        if self.is_healthy():
            recommendations.append("Cluster is healthy - continue regular monitoring")
            return recommendations

        critical_checks = self.get_critical_checks()
        warning_checks = self.get_warning_checks()

        if critical_checks:
            recommendations.append(
                f"🔴 Address {len(critical_checks)} critical issue(s) immediately"
            )
            for check in critical_checks[:3]:  # Show top 3 critical issues
                recommendations.append(f"   - {check.summary}")

        if warning_checks:
            recommendations.append(
                f"🟡 Investigate {len(warning_checks)} warning(s) when possible"
            )
            for check in warning_checks[:2]:  # Show top 2 warnings
                recommendations.append(f"   - {check.summary}")

        recommendations.append("📊 Monitor cluster status regularly for changes")

        return recommendations

    def get_executive_summary(self) -> str:
        """Get a one-line executive summary suitable for dashboards."""
        status_emoji = {
            HealthStatus.OK: "🟢",
            HealthStatus.WARN: "🟡",
            HealthStatus.ERR: "🔴",
        }

        emoji = status_emoji.get(self.status, "⚪")
        score = self.get_health_score()

        if self.is_healthy():
            return f"{emoji} Cluster is healthy (Score: {score}/100)"
        issues = len(self.checks)
        return (
            f"{emoji} Cluster has {issues} issue(s) requiring attention "
            f"(Score: {score}/100)"
        )
