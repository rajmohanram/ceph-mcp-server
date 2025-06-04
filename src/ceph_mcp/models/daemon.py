"""
Daemon Domain Models

This module contains all data models related to Ceph daemons.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class Daemon(BaseModel):
    """Represents a Ceph daemon with all its attributes."""

    daemon_type: str = Field(..., description="Type of daemon (mon, mgr, osd, etc.)")
    daemon_id: str = Field(..., description="Unique daemon identifier")
    daemon_name: str = Field(..., description="Full daemon name")
    hostname: str = Field(..., description="Host where daemon is running")

    # Resource usage
    memory_usage: int = Field(default=0, description="Memory usage in bytes")
    memory_request: int = Field(default=0, description="Memory request in bytes")
    cpu_percentage: str = Field(default="0%", description="CPU usage percentage")

    # Daemon information
    version: str = Field(default="", description="Ceph version")
    status: int = Field(default=0, description="Daemon status code")
    status_desc: str = Field(default="", description="Daemon status description")
    systemd_unit: str = Field(default="", description="Systemd unit name")
    started: str = Field(default="", description="Start time in ISO format")

    def is_running(self) -> bool:
        """Check if the daemon is running."""
        return self.status == 1 or str(self.status_desc).lower() == "running"

    def is_stopped(self) -> bool:
        """Check if the daemon is stopped."""
        return not self.is_running()

    def get_status_display(self) -> str:
        """Get display-friendly status."""
        return "running" if self.is_running() else "stopped"

    def get_memory_usage_gb(self) -> float:
        """Get memory usage in GB."""
        return round(self.memory_usage / 1024 / 1024 / 1024, 2)

    def get_memory_request_gb(self) -> float:
        """Get memory request in GB."""
        return round(self.memory_request / 1024 / 1024 / 1024, 2)

    def get_cpu_percentage_float(self) -> float:
        """Get CPU percentage as float."""
        try:
            return float(self.cpu_percentage.replace("%", ""))
        except (ValueError, AttributeError):
            return 0.0

    def get_started_datetime(self) -> datetime | None:
        """Get started time as datetime object."""
        try:
            return datetime.fromisoformat(self.started.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return None


class DaemonTypeSummary(BaseModel):
    """Summary information for a specific daemon type."""

    daemon_type: str = Field(..., description="Type of daemon")
    total_count: int = Field(..., description="Total number of daemons")
    running_count: int = Field(..., description="Number of running daemons")
    stopped_count: int = Field(..., description="Number of stopped daemons")
    daemon_names: list[str] = Field(..., description="List of daemon names")


class DaemonSummary(BaseModel):
    """Summary information about all daemons in the cluster."""

    total_daemons: int = Field(..., description="Total number of daemons")
    running_daemons: int = Field(..., description="Number of running daemons")
    stopped_daemons: int = Field(..., description="Number of stopped daemons")
    daemon_types: dict[str, DaemonTypeSummary] = Field(
        ..., description="Summary by daemon type"
    )
    daemons: list[Daemon] = Field(..., description="List of all daemons")
    collected_at: datetime = Field(
        default_factory=datetime.now, description="Data collection timestamp"
    )

    def get_daemon_by_name(self, daemon_name: str) -> Daemon | None:
        """Find a daemon by its name."""
        for daemon in self.daemons:
            if daemon.daemon_name == daemon_name:
                return daemon
        return None

    def get_daemon_by_name_and_host(
        self, daemon_name: str, hostname: str
    ) -> Daemon | None:
        """Find a daemon by name and hostname."""
        for daemon in self.daemons:
            if daemon.daemon_name == daemon_name and daemon.hostname == hostname:
                return daemon
        return None

    def get_daemons_by_type(self, daemon_type: str) -> list[Daemon]:
        """Get all daemons of a specific type."""
        return [daemon for daemon in self.daemons if daemon.daemon_type == daemon_type]

    def get_running_daemons(self) -> list[Daemon]:
        """Get list of running daemons."""
        return [daemon for daemon in self.daemons if daemon.is_running()]

    def get_stopped_daemons(self) -> list[Daemon]:
        """Get list of stopped daemons."""
        return [daemon for daemon in self.daemons if daemon.is_stopped()]

    def get_daemon_types(self) -> list[str]:
        """Get list of unique daemon types."""
        return list(dict(self.daemon_types).keys()) if self.daemon_types else []


class DaemonTypeInfo(BaseModel):
    """Information about daemons of a specific type."""

    daemon_type: str = Field(..., description="Type of daemon")
    daemon_names: list[str] = Field(..., description="List of daemon names")
    total_count: int = Field(..., description="Total number of daemons")
    running_count: int = Field(..., description="Number of running daemons")
    stopped_count: int = Field(..., description="Number of stopped daemons")
    collected_at: datetime = Field(
        default_factory=datetime.now, description="Data collection timestamp"
    )
