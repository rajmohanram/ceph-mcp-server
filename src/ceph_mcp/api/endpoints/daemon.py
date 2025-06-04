"""Daemon-related API endpoints."""

from collections import defaultdict

from ceph_mcp.api.base import BaseCephClient, CephAPIError
from ceph_mcp.models.daemon import (
    Daemon,
    DaemonSummary,
    DaemonTypeInfo,
    DaemonTypeSummary,
)


class DaemonClient(BaseCephClient):  # pylint: disable=too-few-public-methods
    """Client for Ceph daemon-related operations."""

    async def get_daemon_summary(self) -> DaemonSummary:
        """Retrieve summary information about all daemons in the cluster."""
        try:
            response_data = await self._make_request(
                "/api/daemon",
                accept_header="application/vnd.ceph.api.v1.0+json",
            )

            # Response should be a list of daemon objects
            daemons_data = response_data if isinstance(response_data, list) else []

            daemons = []
            for daemon_data in daemons_data:
                daemons.append(self._parse_daemon_data(daemon_data))

            # Calculate summary statistics
            total_daemons = len(daemons)
            running_daemons = len([daemon for daemon in daemons if daemon.is_running()])
            stopped_daemons = total_daemons - running_daemons

            # Group by daemon type
            daemon_types = {}
            type_groups = defaultdict(list)

            for daemon in daemons:
                type_groups[daemon.daemon_type].append(daemon)

            for daemon_type, type_daemons in type_groups.items():
                running_count = len([d for d in type_daemons if d.is_running()])
                stopped_count = len(type_daemons) - running_count

                daemon_types[daemon_type] = DaemonTypeSummary(
                    daemon_type=daemon_type,
                    total_count=len(type_daemons),
                    running_count=running_count,
                    stopped_count=stopped_count,
                    daemon_names=[d.daemon_name for d in type_daemons],
                )

            return DaemonSummary(
                total_daemons=total_daemons,
                running_daemons=running_daemons,
                stopped_daemons=stopped_daemons,
                daemon_types=daemon_types,
                daemons=daemons,
            )

        except Exception as e:
            self.logger.error("Failed to retrieve daemon summary", error=str(e))
            raise CephAPIError(f"Failed to get daemon summary: {str(e)}") from e

    async def get_daemon_names_by_type(self, daemon_type: str) -> DaemonTypeInfo:
        """Retrieve information about all daemons of a specific type."""
        try:
            # Get all daemons first
            daemon_summary = await self.get_daemon_summary()

            # Filter by daemon type
            type_daemons = daemon_summary.get_daemons_by_type(daemon_type)

            if not type_daemons:
                # Check if the daemon type exists at all
                available_types = daemon_summary.get_daemon_types()
                if daemon_type not in available_types:
                    raise CephAPIError(
                        f"Daemon type '{daemon_type}' not found. Available types: {', '.join(available_types)}"
                    )

            running_count = len([d for d in type_daemons if d.is_running()])
            stopped_count = len(type_daemons) - running_count

            return DaemonTypeInfo(
                daemon_type=daemon_type,
                daemon_names=[daemon.daemon_name for daemon in type_daemons],
                total_count=len(type_daemons),
                running_count=running_count,
                stopped_count=stopped_count,
            )

        except CephAPIError:
            # Re-raise CephAPIError as-is
            raise
        except Exception as e:
            self.logger.error(
                "Failed to retrieve daemon names by type",
                daemon_type=daemon_type,
                error=str(e),
            )
            raise CephAPIError(
                f"Failed to get daemon names for type '{daemon_type}': {str(e)}"
            ) from e

    async def get_daemon_details(self, hostname: str, daemon_name: str) -> Daemon:
        """Retrieve detailed information about a specific daemon."""
        try:
            # Get all daemons first (since there's no single daemon endpoint)
            daemon_summary = await self.get_daemon_summary()

            # Find the specific daemon
            daemon = daemon_summary.get_daemon_by_name_and_host(daemon_name, hostname)
            if not daemon:
                raise CephAPIError(
                    f"Daemon '{daemon_name}' not found on host '{hostname}'"
                )

            return daemon

        except CephAPIError:
            # Re-raise CephAPIError as-is
            raise
        except Exception as e:
            self.logger.error(
                "Failed to retrieve daemon details",
                hostname=hostname,
                daemon_name=daemon_name,
                error=str(e),
            )
            raise CephAPIError(
                f"Failed to get daemon details for '{daemon_name}' on '{hostname}': {str(e)}"
            ) from e

    async def perform_daemon_action(self, daemon_name: str, action: str) -> dict:
        """Perform an action on a specific daemon."""
        try:
            # Validate action
            valid_actions = ["start", "stop", "restart"]
            if action not in valid_actions:
                raise CephAPIError(
                    f"Invalid action '{action}'. Valid actions: {', '.join(valid_actions)}"
                )

            # Prepare request payload
            action_payload = {"action": action}

            response_data = await self._make_request(
                f"/api/daemon/{daemon_name}",
                accept_header="application/vnd.ceph.api.v0.1+json",
                method="PUT",
                json_data=action_payload,
            )

            return {
                "daemon_name": daemon_name,
                "action": action,
                "success": True,
                "response": response_data,
            }

        except CephAPIError:
            # Re-raise CephAPIError as-is
            raise
        except Exception as e:
            self.logger.error(
                "Failed to perform daemon action",
                daemon_name=daemon_name,
                action=action,
                error=str(e),
            )
            raise CephAPIError(
                f"Failed to {action} daemon '{daemon_name}': {str(e)}"
            ) from e

    def _parse_daemon_data(self, daemon_data: dict) -> Daemon:
        """Convert raw daemon data to Daemon model."""
        try:
            return Daemon(
                daemon_type=daemon_data.get("daemon_type", "unknown"),
                daemon_id=daemon_data.get("daemon_id", ""),
                daemon_name=daemon_data.get("daemon_name", ""),
                hostname=daemon_data.get("hostname", ""),
                memory_usage=daemon_data.get("memory_usage", 0),
                memory_request=daemon_data.get("memory_request", 0),
                cpu_percentage=daemon_data.get("cpu_percentage", "0%"),
                version=daemon_data.get("version", ""),
                status=daemon_data.get("status", 0),
                status_desc=daemon_data.get("status_desc", ""),
                systemd_unit=daemon_data.get("systemd_unit", ""),
                started=daemon_data.get("started", ""),
            )

        except Exception as e:  # pylint: disable=broad-except
            self.logger.error(
                "Failed to parse daemon data", daemon_data=daemon_data, error=str(e)
            )
            # Return a minimal daemon object with whatever we can extract
            return Daemon(
                daemon_type=daemon_data.get("daemon_type", "unknown"),
                daemon_id=daemon_data.get("daemon_id", ""),
                daemon_name=daemon_data.get("daemon_name", "unknown"),
                hostname=daemon_data.get("hostname", ""),
            )
