"""
CephFS Domain Models

This module contains all data models related to Ceph Filesystems.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class MDSMap(BaseModel):
    """MDS map information for a filesystem."""

    fs_name: str = Field(..., description="Filesystem name")


class CephFS(BaseModel):
    """Represents a Ceph Filesystem with all its attributes."""

    id: int = Field(..., description="Filesystem ID")
    mdsmap: MDSMap = Field(..., description="MDS map information")

    def get_fs_name(self) -> str:
        """Get filesystem name."""
        return str(self.mdsmap.fs_name)

    def get_fs_id(self) -> int:
        """Get filesystem ID."""
        return int(self.id)

    def get_display_name(self) -> str:
        """Get display-friendly name with ID."""
        return f"{self.get_fs_name()} (ID: {self.get_fs_id()})"


class CephFSSummary(BaseModel):
    """Summary information about all CephFS filesystems in the cluster."""

    total_filesystems: int = Field(..., description="Total number of filesystems")
    filesystems: list[CephFS] = Field(..., description="List of all filesystems")
    filesystem_names: list[str] = Field(..., description="List of filesystem names")
    filesystem_ids: list[int] = Field(..., description="List of filesystem IDs")
    collected_at: datetime = Field(
        default_factory=datetime.now, description="Data collection timestamp"
    )

    def get_filesystem_by_id(self, fs_id: int) -> CephFS | None:
        """Find a filesystem by its ID."""
        for fs in self.filesystems:
            if fs.get_fs_id() == fs_id:
                return fs
        return None

    def get_filesystem_by_name(self, fs_name: str) -> CephFS | None:
        """Find a filesystem by its name."""
        for fs in self.filesystems:
            if fs.get_fs_name() == fs_name:
                return fs
        return None

    def get_filesystem_names(self) -> list[str]:
        """Get list of all filesystem names."""
        return [fs.get_fs_name() for fs in self.filesystems]

    def get_filesystem_ids(self) -> list[int]:
        """Get list of all filesystem IDs."""
        return [fs.get_fs_id() for fs in self.filesystems]

    def get_name_id_mapping(self) -> dict[str, int]:
        """Get mapping of filesystem names to IDs."""
        return {fs.get_fs_name(): fs.get_fs_id() for fs in self.filesystems}

    def get_summary_text(self) -> str:
        """Get a human-readable summary."""
        if self.total_filesystems == 0:
            return "No CephFS filesystems found"
        elif self.total_filesystems == 1:
            fs = self.filesystems[0]
            return f"1 filesystem: {fs.get_display_name()}"
        else:
            names = ", ".join([fs.get_fs_name() for fs in self.filesystems])
            return f"{self.total_filesystems} filesystems: {names}"


class CephFSRank(BaseModel):
    """MDS rank information."""

    rank: int
    state: str
    mds: str


class CephFSPool(BaseModel):
    """Pool information."""

    pool: str
    type: str
    used: int  # bytes
    avail: int  # bytes

    def get_used_gb(self) -> float:
        """Get used space in GB."""
        return self.used / (1024**3)

    def get_total_gb(self) -> float:
        """Get total space in GB."""
        return (self.used + self.avail) / (1024**3)

    def get_used_percent(self) -> float:
        """Get usage percentage."""
        total = self.used + self.avail
        return (self.used / total) * 100 if total > 0 else 0.0


class CephFSDetails(BaseModel):
    """Detailed CephFS filesystem information."""

    id: int
    name: str
    client_count: int
    ranks: list[CephFSRank]
    pools: list[CephFSPool]
    collected_at: datetime = Field(default_factory=datetime.now)

    def get_metadata_pool(self) -> CephFSPool | None:
        """Get metadata pool."""
        return next((p for p in self.pools if p.type == "metadata"), None)

    def get_data_pool(self) -> CephFSPool | None:
        """Get data pool."""
        return next((p for p in self.pools if p.type == "data"), None)
