"""OSD-related API endpoints."""

from collections import defaultdict

from ceph_mcp.api.base import BaseCephClient, CephAPIError
from ceph_mcp.models.osd import (
    OSD,
    DeviceClassSummary,
    Host,
    OSDIdInfo,
    OSDStats,
    OSDSummary,
    PerfStat,
    Tree,
)


class OSDClient(BaseCephClient):  # pylint: disable=too-few-public-methods
    """Client for Ceph OSD-related operations."""

    async def get_osd_summary(self) -> OSDSummary:
        """Retrieve summary information about all OSDs in the cluster."""
        try:
            response_data = await self._make_request(
                "/api/osd?limit=-1",
                accept_header="application/vnd.ceph.api.v1.1+json",
            )

            # Response should be a list of OSD objects
            osds_data = response_data if isinstance(response_data, list) else []

            osds = []
            for osd_data in osds_data:
                osds.append(self._parse_osd_data(osd_data))

            # Calculate summary statistics
            total_osds = len(osds)
            up_osds = len([osd for osd in osds if osd.is_up()])
            down_osds = total_osds - up_osds
            in_osds = len([osd for osd in osds if osd.is_in()])
            out_osds = total_osds - in_osds
            working_osds = len([osd for osd in osds if osd.is_working()])

            # Get unique hosts
            unique_hosts = list({osd.get_hostname() for osd in osds})

            # Get unique device classes
            device_classes = list({osd.get_device_class() for osd in osds})

            # Group by device class for summary
            device_class_summary = {}
            device_groups = defaultdict(list)

            for osd in osds:
                device_groups[osd.get_device_class()].append(osd)

            for device_class, class_osds in device_groups.items():
                total_pgs = sum(osd.osd_stats.num_pgs for osd in class_osds)
                total_capacity = sum(osd.osd_stats.kb for osd in class_osds)
                total_used = sum(osd.osd_stats.kb_used for osd in class_osds)
                total_available = sum(osd.osd_stats.kb_avail for osd in class_osds)

                device_class_summary[device_class] = DeviceClassSummary(
                    device_class=device_class,
                    osd_count=len(class_osds),
                    total_pgs=total_pgs,
                    total_capacity_kb=total_capacity,
                    total_used_kb=total_used,
                    total_available_kb=total_available,
                )

            return OSDSummary(
                total_osds=total_osds,
                up_osds=up_osds,
                down_osds=down_osds,
                in_osds=in_osds,
                out_osds=out_osds,
                working_osds=working_osds,
                unique_hosts=unique_hosts,
                device_classes=device_classes,
                device_class_summary=device_class_summary,
                osds=osds,
            )

        except Exception as e:
            self.logger.error("Failed to retrieve OSD summary", error=str(e))
            raise CephAPIError(f"Failed to get OSD summary: {str(e)}") from e

    async def get_osd_ids(self) -> OSDIdInfo:
        """Retrieve list of all OSD IDs and their hosts."""
        try:
            # Get all OSDs first
            osd_summary = await self.get_osd_summary()

            # Extract OSD ID and host information
            osd_ids = [
                {"osd_id": osd.osd, "hostname": osd.get_hostname()}
                for osd in osd_summary.osds
            ]

            return OSDIdInfo(osd_ids=osd_ids, total_count=len(osd_ids))

        except Exception as e:
            self.logger.error("Failed to retrieve OSD IDs", error=str(e))
            raise CephAPIError(f"Failed to get OSD IDs: {str(e)}") from e

    async def get_osd_details(self, osd_id: int) -> OSD:
        """Retrieve detailed information about a specific OSD."""
        try:
            # Get all OSDs first (since there's no single OSD endpoint)
            osd_summary = await self.get_osd_summary()

            # Find the specific OSD
            osd = osd_summary.get_osd_by_id(osd_id)
            if not osd:
                available_ids = [str(osd.osd) for osd in osd_summary.osds]
                raise CephAPIError(
                    f"OSD {osd_id} not found. Available OSD IDs: {', '.join(available_ids)}"
                )

            return osd

        except CephAPIError:
            # Re-raise CephAPIError as-is
            raise
        except Exception as e:
            self.logger.error(
                "Failed to retrieve OSD details", osd_id=osd_id, error=str(e)
            )
            raise CephAPIError(
                f"Failed to get OSD details for OSD {osd_id}: {str(e)}"
            ) from e

    def _parse_osd_data(self, osd_data: dict) -> OSD:
        """Convert raw OSD data to OSD model."""
        try:
            # Parse nested structures
            osd_stats_data = osd_data.get("osd_stats", {})
            tree_data = osd_data.get("tree", {})
            host_data = osd_data.get("host", {})

            # Parse performance statistics
            perf_stat_data = osd_stats_data.get("perf_stat", {})
            perf_stat = PerfStat(
                commit_latency_ms=perf_stat_data.get("commit_latency_ms", 0.0),
                apply_latency_ms=perf_stat_data.get("apply_latency_ms", 0.0),
            )

            # Parse OSD statistics
            osd_stats = OSDStats(
                osd=osd_stats_data.get("osd", 0),
                num_pgs=osd_stats_data.get("num_pgs", 0),
                num_osds=osd_stats_data.get("num_osds", 1),
                kb=osd_stats_data.get("kb", 0),
                kb_used=osd_stats_data.get("kb_used", 0),
                kb_avail=osd_stats_data.get("kb_avail", 0),
                perf_stat=perf_stat,
                alerts=osd_stats_data.get("alerts", []),
            )

            # Parse tree information
            tree = Tree(
                id=tree_data.get("id", 0),
                device_class=tree_data.get("device_class", ""),
                type=tree_data.get("type", "osd"),
            )

            # Parse host information
            host = Host(name=host_data.get("name", "unknown"))

            return OSD(
                osd=osd_data.get("osd", 0),
                id=osd_data.get("id", 0),
                up=osd_data.get("up", 0),
                **{"in": osd_data.get("in", 0)},
                weight=osd_data.get("weight", 1.0),
                operational_status=osd_data.get("operational_status", ""),
                osd_stats=osd_stats,
                tree=tree,
                host=host,
            )

        except Exception as e:  # pylint: disable=broad-except
            self.logger.error(
                "Failed to parse OSD data", osd_data=osd_data, error=str(e)
            )
            # Return a minimal OSD object with whatever we can extract
            return OSD(
                osd=osd_data.get("osd", 0),
                id=osd_data.get("id", 0),
                up=osd_data.get("up", 0),
                **{"in": osd_data.get("in", 0)},
                weight=osd_data.get("weight", 1.0),
                operational_status=osd_data.get("operational_status", ""),
                osd_stats=OSDStats(osd=osd_data.get("osd", 0)),
                tree=Tree(id=osd_data.get("id", 0)),
                host=Host(name="unknown"),
            )
