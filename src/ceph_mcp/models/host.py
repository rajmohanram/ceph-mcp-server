"""
Host Domain Models

This module contains all data models related to Ceph hosts.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ServiceInstance(BaseModel):
    """Represents a service instance on a host."""

    type: str = Field(..., description="Service type (mon, mgr, osd, etc.)")
    count: int = Field(..., description="Number of instances of this service")


class Host(BaseModel):
    """Represents a Ceph cluster host with all its attributes."""

    hostname: str = Field(..., description="Host name")
    addr: str = Field(..., description="IP address")
    status: str = Field(..., description="Host status")
    labels: list[str] = Field(default_factory=list, description="Host labels")

    # Service information
    service_instances: list[ServiceInstance] = Field(
        default_factory=list, description="Services running on this host"
    )

    # Hardware information
    arch: str = Field(default="", description="CPU architecture")
    cpu_cores: int = Field(default=0, description="Number of CPU cores")
    cpu_count: int = Field(default=0, description="Number of CPUs")
    cpu_threads: int = Field(default=0, description="Number of CPU threads")
    cpu_model: str = Field(default="", description="CPU model")

    # Memory information (in KB)
    memory_total_kb: int = Field(default=0, description="Total memory in KB")
    memory_available_kb: int = Field(default=0, description="Available memory in KB")
    memory_free_kb: int = Field(default=0, description="Free memory in KB")

    # System information
    operating_system: str = Field(default="", description="Operating system")
    kernel: str = Field(default="", description="Kernel version")
    fqdn: str = Field(default="", description="Fully qualified domain name")
    shortname: str = Field(default="", description="Short hostname")
    system_uptime: float = Field(default=0.0, description="System uptime in seconds")
    timestamp: float = Field(default=0.0, description="Timestamp of data collection")

    def is_online(self) -> bool:
        """Check if the host is online."""
        # If status is empty string, consider it online
        return self.status == "" or str(self.status).lower() == "online"

    def is_offline(self) -> bool:
        """Check if the host is offline."""
        return not self.is_online()

    def get_status_display(self) -> str:
        """Get display-friendly status."""
        return "online" if self.is_online() else self.status

    def get_memory_total_gb(self) -> float:
        """Get total memory in GB."""
        return round(self.memory_total_kb / 1024 / 1024, 2)

    def get_memory_free_gb(self) -> float:
        """Get free memory in GB."""
        return round(self.memory_free_kb / 1024 / 1024, 2)

    def get_memory_available_gb(self) -> float:
        """Get available memory in GB."""
        return round(self.memory_available_kb / 1024 / 1024, 2)

    def get_service_summary(self) -> str:
        """Get a summary of services running on this host."""
        if not self.service_instances:
            return "No services"

        service_parts = []
        for service in self.service_instances:
            service_parts.append(f"{service.type}({service.count})")

        return ", ".join(service_parts)

    def get_uptime_days(self) -> float:
        """Get system uptime in days."""
        return round(self.system_uptime / 86400, 1)


class HostSummary(BaseModel):
    """Summary information about all hosts in the cluster."""

    total_hosts: int = Field(..., description="Total number of hosts")
    online_hosts: int = Field(..., description="Number of online hosts")
    offline_hosts: int = Field(..., description="Number of offline hosts")
    hosts: list[Host] = Field(..., description="List of all hosts")
    collected_at: datetime = Field(
        default_factory=datetime.now, description="Data collection timestamp"
    )

    def get_host_by_hostname(self, hostname: str) -> Host | None:
        """Find a host by hostname."""
        for host in self.hosts:
            if hostname in (host.hostname, host.shortname, host.fqdn):
                return host
        return None

    def get_online_hosts(self) -> list[Host]:
        """Get list of online hosts."""
        return [host for host in self.hosts if host.is_online()]

    def get_offline_hosts(self) -> list[Host]:
        """Get list of offline hosts."""
        return [host for host in self.hosts if host.is_offline()]
