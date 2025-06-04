"""
OSD Domain Models

This module contains all data models related to Ceph OSDs.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class PerfStat(BaseModel):
    """Performance statistics for an OSD."""

    commit_latency_ms: float = Field(
        default=0.0, description="Commit latency in milliseconds"
    )
    apply_latency_ms: float = Field(
        default=0.0, description="Apply latency in milliseconds"
    )


class OSDStats(BaseModel):
    """Statistics for an OSD."""

    osd: int = Field(..., description="OSD ID")
    num_pgs: int = Field(default=0, description="Number of placement groups")
    num_osds: int = Field(default=1, description="Number of OSDs")

    # Storage capacity in KB
    kb: int = Field(default=0, description="Total capacity in KB")
    kb_used: int = Field(default=0, description="Used capacity in KB")
    kb_avail: int = Field(default=0, description="Available capacity in KB")

    perf_stat: PerfStat = Field(
        default_factory=PerfStat, description="Performance statistics"
    )
    alerts: list[Any] = Field(default_factory=list, description="OSD alerts")


class Tree(BaseModel):
    """Tree information for an OSD."""

    id: int = Field(..., description="Tree ID")
    device_class: str = Field(default="", description="Device class (ssd, hdd, nvme)")
    type: str = Field(default="osd", description="Node type")


class Host(BaseModel):
    """Host information for an OSD."""

    name: str = Field(..., description="Host name")


class OSD(BaseModel):
    """Represents a Ceph OSD with all its attributes."""

    osd: int = Field(..., description="OSD ID")
    id: int = Field(..., description="OSD ID (duplicate)")
    up: int = Field(..., description="Up status (1=up, 0=down)")
    in_: int = Field(..., alias="in", description="In status (1=in, 0=out)")
    weight: float = Field(default=1.0, description="OSD weight")
    operational_status: str = Field(default="", description="Operational status")

    # Nested objects
    osd_stats: OSDStats = Field(..., description="OSD statistics")
    tree: Tree = Field(..., description="Tree information")
    host: Host = Field(..., description="Host information")

    def is_up(self) -> bool:
        """Check if the OSD is up."""
        return self.up == 1

    def is_down(self) -> bool:
        """Check if the OSD is down."""
        return self.up == 0

    def is_in(self) -> bool:
        """Check if the OSD is in."""
        return self.in_ == 1

    def is_out(self) -> bool:
        """Check if the OSD is out."""
        return self.in_ == 0

    def is_working(self) -> bool:
        """Check if the OSD is working."""
        return str(self.operational_status).lower() == "working"

    def get_status_display(self) -> str:
        """Get display-friendly status."""
        status_parts = []
        status_parts.append("up" if self.is_up() else "down")
        status_parts.append("in" if self.is_in() else "out")
        return f"{'/'.join(status_parts)} ({self.operational_status})"

    def get_capacity_gb(self) -> float:
        """Get total capacity in GB."""
        return round(int(self.osd_stats.kb) / 1024 / 1024, 2)

    def get_used_gb(self) -> float:
        """Get used capacity in GB."""
        return round(int(self.osd_stats.kb_used) / 1024 / 1024, 2)

    def get_available_gb(self) -> float:
        """Get available capacity in GB."""
        return round(int(self.osd_stats.kb_avail) / 1024 / 1024, 2)

    def get_usage_percentage(self) -> float:
        """Get usage percentage."""
        if self.osd_stats.kb == 0:
            return 0.0
        return round((self.osd_stats.kb_used / self.osd_stats.kb) * 100, 2)

    def get_device_class(self) -> str:
        """Get device class."""
        return str(self.tree.device_class) or "unknown"

    def get_hostname(self) -> str:
        """Get hostname."""
        return str(self.host.name)


class DeviceClassSummary(BaseModel):
    """Summary information for a specific device class."""

    device_class: str = Field(..., description="Device class name")
    osd_count: int = Field(..., description="Number of OSDs")
    total_pgs: int = Field(..., description="Total number of placement groups")
    total_capacity_kb: int = Field(..., description="Total capacity in KB")
    total_used_kb: int = Field(..., description="Total used capacity in KB")
    total_available_kb: int = Field(..., description="Total available capacity in KB")

    def get_total_capacity_gb(self) -> float:
        """Get total capacity in GB."""
        return round(self.total_capacity_kb / 1024 / 1024, 2)

    def get_total_used_gb(self) -> float:
        """Get total used capacity in GB."""
        return round(self.total_used_kb / 1024 / 1024, 2)

    def get_total_available_gb(self) -> float:
        """Get total available capacity in GB."""
        return round(self.total_available_kb / 1024 / 1024, 2)


class OSDSummary(BaseModel):
    """Summary information about all OSDs in the cluster."""

    total_osds: int = Field(..., description="Total number of OSDs")
    up_osds: int = Field(..., description="Number of up OSDs")
    down_osds: int = Field(..., description="Number of down OSDs")
    in_osds: int = Field(..., description="Number of in OSDs")
    out_osds: int = Field(..., description="Number of out OSDs")
    working_osds: int = Field(..., description="Number of working OSDs")

    unique_hosts: list[str] = Field(..., description="List of unique host names")
    device_classes: list[str] = Field(..., description="List of unique device classes")
    device_class_summary: dict[str, DeviceClassSummary] = Field(
        ..., description="Summary by device class"
    )

    osds: list[OSD] = Field(..., description="List of all OSDs")
    collected_at: datetime = Field(
        default_factory=datetime.now, description="Data collection timestamp"
    )

    def get_osd_by_id(self, osd_id: int) -> OSD | None:
        """Find an OSD by its ID."""
        for osd in self.osds:
            if osd.osd == osd_id:
                return osd
        return None

    def get_osds_by_host(self, hostname: str) -> list[OSD]:
        """Get all OSDs on a specific host."""
        return [osd for osd in self.osds if osd.get_hostname() == hostname]

    def get_osds_by_device_class(self, device_class: str) -> list[OSD]:
        """Get all OSDs of a specific device class."""
        return [osd for osd in self.osds if osd.get_device_class() == device_class]

    def get_up_osds(self) -> list[OSD]:
        """Get list of up OSDs."""
        return [osd for osd in self.osds if osd.is_up()]

    def get_down_osds(self) -> list[OSD]:
        """Get list of down OSDs."""
        return [osd for osd in self.osds if osd.is_down()]

    def get_working_osds(self) -> list[OSD]:
        """Get list of working OSDs."""
        return [osd for osd in self.osds if osd.is_working()]


class OSDIdInfo(BaseModel):
    """Information about OSD IDs and their hosts."""

    osd_ids: list[dict[str, Any]] = Field(
        ..., description="List of OSD ID and host mappings"
    )
    total_count: int = Field(..., description="Total number of OSDs")
    collected_at: datetime = Field(
        default_factory=datetime.now, description="Data collection timestamp"
    )
