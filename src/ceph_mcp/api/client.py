"""Main client that combines all endpoint clients."""

from ceph_mcp.api.endpoints.daemon import DaemonClient
from ceph_mcp.api.endpoints.health import HealthClient
from ceph_mcp.api.endpoints.host import HostClient
from ceph_mcp.api.endpoints.osd import OSDClient
from ceph_mcp.models.daemon import Daemon, DaemonSummary, DaemonTypeInfo
from ceph_mcp.models.health import ClusterHealth
from ceph_mcp.models.host import Host, HostSummary
from ceph_mcp.models.osd import OSD, OSDIdInfo, OSDSummary


class CephClient:
    """
    Main Ceph client that provides access to all endpoint clients.

    This is the primary interface that the MCP handlers will use.
    It provides both individual endpoint access and convenience methods
    that combine multiple endpoints.
    """

    def __init__(self) -> None:
        self.health: HealthClient = HealthClient()
        self.host: HostClient = HostClient()
        self.daemon: DaemonClient = DaemonClient()
        self.osd: OSDClient = OSDClient()

    async def __aenter__(self):
        """Initialize all endpoint clients."""
        # self.health = HealthClient()

        # Enter all clients
        await self.health.__aenter__()
        await self.host.__aenter__()
        await self.daemon.__aenter__()
        await self.osd.__aenter__()

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up all endpoint clients."""
        if self.health:
            await self.health.__aexit__(exc_type, exc_val, exc_tb)
        if self.host:
            await self.host.__aexit__(exc_type, exc_val, exc_tb)
        if self.daemon:
            await self.daemon.__aexit__(exc_type, exc_val, exc_tb)
        if self.osd:
            await self.osd.__aexit__(exc_type, exc_val, exc_tb)

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

    # Convenience methods that combine multiple endpoints
    # async def get_cluster_status(self) -> ClusterStatus:
    #     """Get comprehensive cluster status combining health and host information."""
    #     if not self.health:
    #         raise RuntimeError("Client not properly initialized")

    #     health = await self.health.get_cluster_health()

    #     total_hosts = len(health.hosts)
    #     online_hosts = sum(1 for host in health.hosts if host.is_online())
    #     total_osds = sum(host.get_osd_count() for host in health.hosts)

    #     return ClusterStatus(
    #         health=health,
    #         hosts=health.hosts,
    #         total_hosts=total_hosts,
    #         online_hosts=online_hosts,
    #         total_osds=total_osds,
    #         up_osds=total_osds,  # Would need OSD client for accurate count
    #         in_osds=total_osds,  # Would need OSD client for accurate count
    #     )
