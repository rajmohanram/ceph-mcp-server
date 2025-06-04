"""Pool-related API endpoints."""

from collections import defaultdict

from ceph_mcp.api.base import BaseCephClient, CephAPIError
from ceph_mcp.models.pool import (
    Pool,
    PoolOptions,
    PoolStateSummary,
    PoolSummary,
    PoolTypeSummary,
)


class PoolClient(BaseCephClient):  # pylint: disable=too-few-public-methods
    """Client for Ceph pool-related operations."""

    async def get_pool_summary(self) -> PoolSummary:
        """Retrieve summary information about all pools in the cluster."""
        try:
            response_data = await self._make_request(
                "/api/pool?stats=true",
                accept_header="application/vnd.ceph.api.v1.0+json",
            )

            # Response should be a list of pool objects
            pools_data = response_data if isinstance(response_data, list) else []

            pools = []
            for pool_data in pools_data:
                pools.append(self._parse_pool_data(pool_data))

            # Calculate summary statistics
            total_pools = len(pools)
            replicated_pools = len([pool for pool in pools if pool.is_replicated()])
            erasure_pools = len([pool for pool in pools if pool.is_erasure()])

            # Group by pool type
            pool_types = {}
            type_groups = defaultdict(list)

            for pool in pools:
                type_groups[pool.type].append(pool)

            for pool_type, type_pools in type_groups.items():
                pool_types[pool_type] = PoolTypeSummary(
                    pool_type=pool_type,
                    count=len(type_pools),
                    pool_names=[p.pool_name for p in type_pools],
                )

            # Aggregate PG status across all pools
            total_pgs = sum(pool.get_total_pgs() for pool in pools)
            pg_state_aggregation = defaultdict(
                lambda: {"pool_count": 0, "total_pgs": 0}
            )

            for pool in pools:
                pool_states = pool.get_pg_states()
                for state in pool_states:
                    pg_state_aggregation[state]["pool_count"] += 1
                    pg_state_aggregation[state]["total_pgs"] += pool.pg_status.get(
                        state, 0
                    )

            # Convert to PoolStateSummary objects
            pg_states = {}
            for state, data in pg_state_aggregation.items():
                pg_states[state] = PoolStateSummary(
                    state=state,
                    pool_count=data["pool_count"],
                    total_pgs=data["total_pgs"],
                )

            # Calculate health statistics
            healthy_pools = len([pool for pool in pools if pool.is_healthy()])
            unhealthy_pools = total_pools - healthy_pools

            return PoolSummary(
                total_pools=total_pools,
                replicated_pools=replicated_pools,
                erasure_pools=erasure_pools,
                pool_types=pool_types,
                total_pgs=total_pgs,
                pg_states=pg_states,
                healthy_pools=healthy_pools,
                unhealthy_pools=unhealthy_pools,
                pools=pools,
            )

        except Exception as e:
            self.logger.error("Failed to retrieve pool summary", error=str(e))
            raise CephAPIError(f"Failed to get pool summary: {str(e)}") from e

    async def get_pool_details(self, pool_name: str) -> Pool:
        """Retrieve detailed information about a specific pool."""
        try:
            # Get all pools first (since there's no single pool endpoint)
            pool_summary = await self.get_pool_summary()

            # Find the specific pool
            pool = pool_summary.get_pool_by_name(pool_name)
            if not pool:
                available_pools = pool_summary.get_pool_names()
                raise CephAPIError(
                    f"Pool '{pool_name}' not found. Available pools: {', '.join(available_pools)}"
                )

            return pool

        except CephAPIError:
            # Re-raise CephAPIError as-is
            raise
        except Exception as e:
            self.logger.error(
                "Failed to retrieve pool details", pool_name=pool_name, error=str(e)
            )
            raise CephAPIError(
                f"Failed to get pool details for '{pool_name}': {str(e)}"
            ) from e

    def _parse_pool_data(self, pool_data: dict) -> Pool:
        """Convert raw pool data to Pool model."""
        try:
            # Parse pool options
            options_data = pool_data.get("options", {})
            options = PoolOptions(
                pg_num_max=options_data.get("pg_num_max", 32),
                pg_num_min=options_data.get("pg_num_min", 1),
            )

            return Pool(
                pool_name=pool_data.get("pool_name", "unknown"),
                type=pool_data.get("type", "unknown"),
                size=pool_data.get("size", 0),
                min_size=pool_data.get("min_size", 0),
                crush_rule=pool_data.get("crush_rule", ""),
                pg_num=pool_data.get("pg_num", 0),
                pg_placement_num=pool_data.get("pg_placement_num", 0),
                pg_placement_num_target=pool_data.get("pg_placement_num_target", 0),
                pg_num_target=pool_data.get("pg_num_target", 0),
                options=options,
                application_metadata=pool_data.get("application_metadata", []),
                pg_status=pool_data.get("pg_status", {}),
            )

        except Exception as e:
            self.logger.error(
                "Failed to parse pool data", pool_data=pool_data, error=str(e)
            )
            # Return a minimal pool object with whatever we can extract
            return Pool(
                pool_name=pool_data.get("pool_name", "unknown"),
                type=pool_data.get("type", "unknown"),
                size=pool_data.get("size", 0),
                min_size=pool_data.get("min_size", 0),
                crush_rule=pool_data.get("crush_rule", ""),
                pg_num=pool_data.get("pg_num", 0),
                pg_placement_num=pool_data.get("pg_placement_num", 0),
                pg_placement_num_target=pool_data.get("pg_placement_num_target", 0),
                pg_num_target=pool_data.get("pg_num_target", 0),
                options=PoolOptions(),
                application_metadata=[],
                pg_status={},
            )
