"""
Pool Domain Models

This module contains all data models related to Ceph pools.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class PoolOptions(BaseModel):
    """Pool configuration options."""

    pg_num_max: int = Field(
        default=32, description="Maximum number of placement groups"
    )
    pg_num_min: int = Field(default=1, description="Minimum number of placement groups")


class Pool(BaseModel):
    """Represents a Ceph pool with all its attributes."""

    pool_name: str = Field(..., description="Name of the pool")
    type: str = Field(..., description="Pool type (replicated or erasure)")
    size: int = Field(..., description="Pool size (number of replicas)")
    min_size: int = Field(..., description="Minimum pool size")
    crush_rule: str = Field(..., description="CRUSH rule name")

    # Placement group configuration
    pg_num: int = Field(..., description="Current number of placement groups")
    pg_placement_num: int = Field(..., description="Current PG placement number")
    pg_placement_num_target: int = Field(..., description="Target PG placement number")
    pg_num_target: int = Field(..., description="Target number of placement groups")

    # Pool options and metadata
    options: PoolOptions = Field(..., description="Pool configuration options")
    application_metadata: list[str] = Field(
        default_factory=list, description="Applications using this pool"
    )
    pg_status: dict[str, int] = Field(
        default_factory=dict, description="Placement group status counts"
    )

    def is_replicated(self) -> bool:
        """Check if the pool is replicated type."""
        return self.type.lower() == "replicated"

    def is_erasure(self) -> bool:
        """Check if the pool is erasure coded."""
        return self.type.lower() == "erasure"

    def get_total_pgs(self) -> int:
        """Get total number of placement groups."""
        return sum(self.pg_status.values()) if self.pg_status else 0

    def get_active_pgs(self) -> int:
        """Get number of active placement groups."""
        active_count = 0
        for status, count in self.pg_status.items():
            if "active" in status.lower():
                active_count += count
        return active_count

    def get_pg_states(self) -> list[str]:
        """Get list of unique PG states."""
        return list(self.pg_status.keys()) if self.pg_status else []

    def is_healthy(self) -> bool:
        """Check if all PGs are in active+clean state."""
        if not self.pg_status:
            return False

        total_pgs = self.get_total_pgs()
        active_clean_pgs = self.pg_status.get("active+clean", 0)

        return total_pgs == active_clean_pgs and total_pgs > 0

    def get_primary_applications(self) -> str:
        """Get primary application or applications as a string."""
        if not self.application_metadata:
            return "none"
        elif len(self.application_metadata) == 1:
            return self.application_metadata[0]
        else:
            return ", ".join(self.application_metadata)

    def get_replica_info(self) -> str:
        """Get replica information as a readable string."""
        return f"{self.min_size}/{self.size}"

    def get_pg_efficiency(self) -> float:
        """Get PG efficiency (active PGs / total PGs)."""
        total = self.get_total_pgs()
        if total == 0:
            return 0.0
        active = self.get_active_pgs()
        return round((active / total) * 100, 1)


class PoolTypeSummary(BaseModel):
    """Summary information for a specific pool type."""

    pool_type: str = Field(..., description="Pool type")
    count: int = Field(..., description="Number of pools of this type")
    pool_names: list[str] = Field(..., description="List of pool names")


class PoolStateSummary(BaseModel):
    """Summary information for pools by PG state."""

    state: str = Field(..., description="PG state")
    pool_count: int = Field(..., description="Number of pools with this state")
    total_pgs: int = Field(..., description="Total PGs in this state")


class PoolSummary(BaseModel):
    """Summary information about all pools in the cluster."""

    total_pools: int = Field(..., description="Total number of pools")
    replicated_pools: int = Field(..., description="Number of replicated pools")
    erasure_pools: int = Field(..., description="Number of erasure coded pools")

    # Pool type breakdown
    pool_types: dict[str, PoolTypeSummary] = Field(
        ..., description="Summary by pool type"
    )

    # PG status aggregation
    total_pgs: int = Field(..., description="Total placement groups across all pools")
    pg_states: dict[str, PoolStateSummary] = Field(
        ..., description="Summary by PG state"
    )

    # Pool health
    healthy_pools: int = Field(
        ..., description="Number of pools with all PGs active+clean"
    )
    unhealthy_pools: int = Field(..., description="Number of pools with PG issues")

    pools: list[Pool] = Field(..., description="List of all pools")
    collected_at: datetime = Field(
        default_factory=datetime.now, description="Data collection timestamp"
    )

    def get_pool_by_name(self, pool_name: str) -> Pool | None:
        """Find a pool by its name."""
        for pool in self.pools:
            if pool.pool_name == pool_name:
                return pool
        return None

    def get_pools_by_type(self, pool_type: str) -> list[Pool]:
        """Get all pools of a specific type."""
        return [pool for pool in self.pools if pool.type.lower() == pool_type.lower()]

    def get_healthy_pools(self) -> list[Pool]:
        """Get list of healthy pools."""
        return [pool for pool in self.pools if pool.is_healthy()]

    def get_unhealthy_pools(self) -> list[Pool]:
        """Get list of unhealthy pools."""
        return [pool for pool in self.pools if not pool.is_healthy()]

    def get_pool_names(self) -> list[str]:
        """Get list of all pool names."""
        return [pool.pool_name for pool in self.pools]

    def get_unique_applications(self) -> list[str]:
        """Get list of unique applications across all pools."""
        applications = set()
        for pool in self.pools:
            applications.update(pool.application_metadata)
        return list(applications)

    def get_average_pool_size(self) -> float:
        """Get average pool size across all pools."""
        if not self.pools:
            return 0.0
        total_size = sum(pool.size for pool in self.pools)
        return round(total_size / len(self.pools), 1)
