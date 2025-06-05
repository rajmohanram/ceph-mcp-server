"""Main client that combines all endpoint clients."""

import httpx

from ceph_mcp.api.base import CephTokenManager
from ceph_mcp.api.endpoints.cephfs import CephFSClient
from ceph_mcp.api.endpoints.daemon import DaemonClient
from ceph_mcp.api.endpoints.health import HealthClient
from ceph_mcp.api.endpoints.host import HostClient
from ceph_mcp.api.endpoints.osd import OSDClient
from ceph_mcp.api.endpoints.pool import PoolClient
from ceph_mcp.config.settings import get_ssl_context, settings
from ceph_mcp.models.cephfs import CephFSDetails, CephFSSummary
from ceph_mcp.models.daemon import Daemon, DaemonSummary, DaemonTypeInfo
from ceph_mcp.models.health import ClusterHealth
from ceph_mcp.models.host import Host, HostSummary
from ceph_mcp.models.osd import OSD, OSDIdInfo, OSDSummary
from ceph_mcp.models.pool import Pool, PoolSummary


class CephClient:
    """
    Main Ceph client that provides access to all endpoint clients.

    This is the primary interface that the MCP handlers will use.
    It provides both individual endpoint access and convenience methods
    that combine multiple endpoints.
    """

    def __init__(self) -> None:
        # Shared resources
        self._shared_session = None
        self._shared_token_manager = None
        self.base_url = str(settings.ceph_manager_url)

        # Create endpoint clients (no auto-initialization)
        self.health: HealthClient = HealthClient()
        self.host: HostClient = HostClient()
        self.daemon: DaemonClient = DaemonClient()
        self.osd: OSDClient = OSDClient()
        self.pool: PoolClient = PoolClient()
        self.cephfs: CephFSClient = CephFSClient()

    async def __aenter__(self):
        """Initialize all endpoint clients with shared session and token manager."""
        # Create shared session once
        self._shared_session = httpx.AsyncClient(
            timeout=settings.request_timeout_seconds,
            verify=get_ssl_context(),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
        )

        # Create shared token manager and authenticate once
        self._shared_token_manager = CephTokenManager(
            self._shared_session, self.base_url
        )
        await self._shared_token_manager.get_token()

        # Inject shared resources into all endpoint clients
        for client in [
            self.health,
            self.host,
            self.daemon,
            self.osd,
            self.pool,
            self.cephfs,
        ]:
            client.session = self._shared_session
            client.token_manager = self._shared_token_manager

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up all endpoint clients."""
        if self._shared_session:
            await self._shared_session.aclose()
        # Reset references
        for client in [
            self.health,
            self.host,
            self.daemon,
            self.osd,
            self.pool,
            self.cephfs,
        ]:
            client.session = None
            client.token_manager = None

    async def get_cluster_health(self) -> ClusterHealth:
        """Get the overall health status of the Ceph cluster."""
        if not self.health:
            raise RuntimeError("Client not properly initialized")

        return await self.health.get_cluster_health()

    async def get_host_summary(self) -> HostSummary:
        """Get summary information about all hosts in the cluster."""
        if not self.host:
            raise RuntimeError("Client not properly initialized")

        return await self.host.get_host_summary()

    async def get_host_details(self, hostname: str) -> Host:
        """Get detailed information about a specific host."""
        if not self.host:
            raise RuntimeError("Client not properly initialized")

        return await self.host.get_host_details(hostname)

    async def get_daemon_summary(self) -> DaemonSummary:
        """Get summary information about all daemons in the cluster."""
        if not self.daemon:
            raise RuntimeError("Client not properly initialized")

        return await self.daemon.get_daemon_summary()

    async def get_daemon_names_by_type(self, daemon_type: str) -> DaemonTypeInfo:
        """Get daemon names for a specific daemon type."""
        if not self.daemon:
            raise RuntimeError("Client not properly initialized")

        return await self.daemon.get_daemon_names_by_type(daemon_type)

    async def get_daemon_details(self, hostname: str, daemon_name: str) -> Daemon:
        """Get detailed information about a specific daemon."""
        if not self.daemon:
            raise RuntimeError("Client not properly initialized")

        return await self.daemon.get_daemon_details(hostname, daemon_name)

    async def perform_daemon_action(self, daemon_name: str, action: str) -> dict:
        """Perform an action on a specific daemon."""
        if not self.daemon:
            raise RuntimeError("Client not properly initialized")

        return await self.daemon.perform_daemon_action(daemon_name, action)

    async def get_osd_summary(self) -> OSDSummary:
        """Get summary information about all OSDs in the cluster."""
        if not self.osd:
            raise RuntimeError("Client not properly initialized")

        return await self.osd.get_osd_summary()

    async def get_osd_ids(self) -> OSDIdInfo:
        """Get list of all OSD IDs and their hosts."""
        if not self.osd:
            raise RuntimeError("Client not properly initialized")

        return await self.osd.get_osd_ids()

    async def get_osd_details(self, osd_id: int) -> OSD:
        """Get detailed information about a specific OSD."""
        if not self.osd:
            raise RuntimeError("Client not properly initialized")

        return await self.osd.get_osd_details(osd_id)

    async def perform_osd_mark_action(self, osd_id: int, action: str) -> dict:
        """Perform a mark action on a specific OSD."""
        if not self.osd:
            raise RuntimeError("Client not properly initialized")

        return await self.osd.perform_osd_mark_action(osd_id, action)

    async def get_pool_summary(self) -> PoolSummary:
        """Get summary information about all pools in the cluster."""
        if not self.pool:
            raise RuntimeError("Client not properly initialized")

        return await self.pool.get_pool_summary()

    async def get_pool_details(self, pool_name: str) -> Pool:
        """Get detailed information about a specific pool."""
        if not self.pool:
            raise RuntimeError("Client not properly initialized")

        return await self.pool.get_pool_details(pool_name)

    async def get_fs_summary(self) -> CephFSSummary:
        "Get summary information about all Ceph FS in the cluster"
        if not self.cephfs:
            raise RuntimeError("Client not properly initialized")

        return await self.cephfs.get_fs_summary()

    async def get_fs_details(self, fs_id: int) -> CephFSDetails:
        """Get detailed information about a specific CephFS filesystem."""
        if not self.cephfs:
            raise RuntimeError("Client not properly initialized")

        return await self.cephfs.get_fs_details(fs_id)
