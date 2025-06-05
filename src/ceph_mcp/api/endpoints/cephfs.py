"""CephFS-related API endpoints."""

from ceph_mcp.api.base import BaseCephClient, CephAPIError
from ceph_mcp.models.cephfs import (
    CephFS,
    CephFSDetails,
    CephFSPool,
    CephFSRank,
    CephFSSummary,
    MDSMap,
)


class CephFSClient(BaseCephClient):  # pylint: disable=too-few-public-methods
    """Client for Ceph Filesystem-related operations."""

    async def get_fs_summary(self) -> CephFSSummary:
        """Retrieve summary information about all CephFS filesystems in the cluster."""
        try:
            response_data = await self._make_request(
                "/api/cephfs", accept_header="application/vnd.ceph.api.v1.0+json"
            )

            # Response should be a list of filesystem objects
            fs_data = response_data if isinstance(response_data, list) else []

            filesystems = []
            for fs_item in fs_data:
                filesystems.append(self._parse_cephfs_data(fs_item))

            # Calculate summary statistics
            total_filesystems = len(filesystems)
            filesystem_names = [fs.get_fs_name() for fs in filesystems]
            filesystem_ids = [fs.get_fs_id() for fs in filesystems]

            return CephFSSummary(
                total_filesystems=total_filesystems,
                filesystems=filesystems,
                filesystem_names=filesystem_names,
                filesystem_ids=filesystem_ids,
            )

        except Exception as e:
            self.logger.error("Failed to retrieve CephFS summary", error=str(e))
            raise CephAPIError(f"Failed to get CephFS summary: {str(e)}") from e

    def _parse_cephfs_data(self, fs_data: dict) -> CephFS:
        """Convert raw CephFS data to CephFS model."""
        try:
            # Parse nested MDS map structure
            mdsmap_data = fs_data.get("mdsmap", {})

            # Parse MDS map
            mdsmap = MDSMap(
                fs_name=mdsmap_data.get("fs_name", "unknown"),
            )

            return CephFS(
                id=fs_data.get("id", 0),
                mdsmap=mdsmap,
            )

        except Exception as e:  # pylint: disable=broad-except
            self.logger.error(
                "Failed to parse CephFS data", fs_data=fs_data, error=str(e)
            )
            # Return a minimal CephFS object with whatever we can extract
            return CephFS(
                id=fs_data.get("id", 0),
                mdsmap=MDSMap(fs_name="unknown"),
            )

    async def get_fs_details(self, fs_id: int) -> CephFSDetails:
        """Retrieve detailed information about a specific CephFS filesystem."""
        try:
            response_data = await self._make_request(
                f"/api/cephfs/{fs_id}",
                accept_header="application/vnd.ceph.api.v1.0+json",
            )

            return self._parse_cephfs_details(response_data)

        except Exception as e:
            self.logger.error(
                "Failed to retrieve CephFS details", fs_id=fs_id, error=str(e)
            )
            raise CephAPIError(
                f"Failed to get CephFS details for ID {fs_id}: {str(e)}"
            ) from e

    def _parse_cephfs_details(self, data: dict) -> CephFSDetails:
        """Convert raw CephFS details data to CephFSDetails model."""
        try:
            cephfs_data = data.get("cephfs", {})

            # Parse ranks
            ranks = []
            for rank_data in cephfs_data.get("ranks", []):
                ranks.append(
                    CephFSRank(
                        rank=rank_data.get("rank", 0),
                        state=rank_data.get("state", "unknown"),
                        mds=rank_data.get("mds", "unknown"),
                    )
                )

            # Parse pools
            pools = []
            for pool_data in cephfs_data.get("pools", []):
                pools.append(
                    CephFSPool(
                        pool=pool_data.get("pool", "unknown"),
                        type=pool_data.get("type", "unknown"),
                        used=pool_data.get("used", 0),
                        avail=pool_data.get("avail", 0),
                    )
                )

            return CephFSDetails(
                id=cephfs_data.get("id", 0),
                name=cephfs_data.get("name", "unknown"),
                client_count=cephfs_data.get("client_count", 0),
                ranks=ranks,
                pools=pools,
            )

        except Exception as e:
            self.logger.error("Failed to parse CephFS details", data=data, error=str(e))
            # Return minimal object
            return CephFSDetails(
                id=0, name="unknown", client_count=0, ranks=[], pools=[]
            )
