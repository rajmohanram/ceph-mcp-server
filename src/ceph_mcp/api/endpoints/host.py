"""Host-related API endpoints."""

from ceph_mcp.api.base import BaseCephClient, CephAPIError
from ceph_mcp.models.host import Host, HostSummary, ServiceInstance


class HostClient(BaseCephClient):  # pylint: disable=too-few-public-methods
    """Client for Ceph host-related operations."""

    async def get_host_summary(self) -> HostSummary:
        """Retrieve summary information about all hosts in the cluster."""
        try:
            response_data = await self._make_request(
                "/api/host?facts=true",
                accept_header="application/vnd.ceph.api.v1.3+json",
            )

            # Response should be a list of host objects
            hosts_data = response_data if isinstance(response_data, list) else []

            hosts = []
            for host_data in hosts_data:
                hosts.append(self._parse_host_data(host_data))

            # Calculate summary statistics
            total_hosts = len(hosts)
            online_hosts = len([host for host in hosts if host.is_online()])
            offline_hosts = total_hosts - online_hosts

            return HostSummary(
                total_hosts=total_hosts,
                online_hosts=online_hosts,
                offline_hosts=offline_hosts,
                hosts=hosts,
            )

        except Exception as e:
            self.logger.error("Failed to retrieve host summary", error=str(e))
            raise CephAPIError(f"Failed to get host summary: {str(e)}") from e

    async def get_host_details(self, hostname: str) -> Host:
        """Retrieve detailed information about a specific host."""
        try:
            # Get all hosts first (since there's no single host endpoint)
            host_summary = await self.get_host_summary()

            # Find the specific host
            host = host_summary.get_host_by_hostname(hostname)
            if not host:
                raise CephAPIError(f"Host '{hostname}' not found in cluster")

            return host

        except CephAPIError:
            # Re-raise CephAPIError as-is
            raise
        except Exception as e:
            self.logger.error(
                "Failed to retrieve host details", hostname=hostname, error=str(e)
            )
            raise CephAPIError(
                f"Failed to get host details for '{hostname}': {str(e)}"
            ) from e

    def _parse_host_data(self, host_data: dict) -> Host:
        """Convert raw host data to Host model."""
        try:
            # Parse service instances
            service_instances = []
            for service_data in host_data.get("service_instances", []):
                service_instances.append(
                    ServiceInstance(
                        type=service_data.get("type", "unknown"),
                        count=service_data.get("count", 0),
                    )
                )

            return Host(
                hostname=host_data.get("hostname", "unknown"),
                addr=host_data.get("addr", ""),
                status=host_data.get("status", ""),
                labels=host_data.get("labels", []),
                service_instances=service_instances,
                arch=host_data.get("arch", ""),
                cpu_cores=host_data.get("cpu_cores", 0),
                cpu_count=host_data.get("cpu_count", 0),
                cpu_threads=host_data.get("cpu_threads", 0),
                cpu_model=host_data.get("cpu_model", ""),
                memory_total_kb=host_data.get("memory_total_kb", 0),
                memory_available_kb=host_data.get("memory_available_kb", 0),
                memory_free_kb=host_data.get("memory_free_kb", 0),
                operating_system=host_data.get("operating_system", ""),
                kernel=host_data.get("kernel", ""),
                fqdn=host_data.get("fqdn", ""),
                shortname=host_data.get("shortname", ""),
                system_uptime=host_data.get("system_uptime", 0.0),
                timestamp=host_data.get("timestamp", 0.0),
            )

        except Exception as e:  # pylint: disable=broad-except
            self.logger.error(
                "Failed to parse host data", host_data=host_data, error=str(e)
            )
            # Return a minimal host object with whatever we can extract
            return Host(
                hostname=host_data.get("hostname", "unknown"),
                addr=host_data.get("addr", ""),
                status=host_data.get("status", ""),
            )
