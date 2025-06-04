"""
Main MCP Server with Modular Handler Architecture using FastMCP
"""

import asyncio
import logging

import structlog
from fastmcp import FastMCP

from ceph_mcp.config.settings import settings
from ceph_mcp.handlers.daemon import DaemonHandlers
from ceph_mcp.handlers.health import HealthHandlers
from ceph_mcp.handlers.host import HostHandlers
from ceph_mcp.handlers.osd import OSDHandlers
from ceph_mcp.handlers.pool import PoolHandlers
from ceph_mcp.resources.health import HealthResources
from ceph_mcp.tools.daemon import DaemonTools
from ceph_mcp.tools.health import HealthTools
from ceph_mcp.tools.host import HostTools
from ceph_mcp.tools.osd import OSDTools
from ceph_mcp.tools.pool import PoolTools


def configure_logging() -> None:
    """Configure both structlog and standard logging to work together."""
    # First, configure standard library logging (this is what your modules use)
    logging.basicConfig(
        format="%(message)s", level=logging.INFO  # structlog will handle formatting
    )

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            (
                structlog.processors.JSONRenderer()
                if settings.log_format == "json"
                else structlog.dev.ConsoleRenderer()
            ),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,  # This ensures compatibility
        cache_logger_on_first_use=True,
    )


class CephMCPServer:  # pylint: disable=too-few-public-methods
    """
    Main MCP Server with modular handler architecture using FastMCP.

    This server uses domain-specific handlers to provide a clean,
    maintainable architecture while presenting a unified interface
    to AI assistants via HTTP/WebSocket.
    """

    def __init__(self) -> None:
        """Initialize the Ceph MCP Server."""
        # Configure logging FIRST, before any other operations
        configure_logging()
        self.logger = structlog.get_logger(__name__)
        # Initialize FastMCP server
        self.mcp: FastMCP = FastMCP(
            name=settings.mcp_server_name, version=settings.mcp_server_version
        )
        # Initialize domain-specific handlers
        self.health_handlers = HealthHandlers()
        self.host_handlers = HostHandlers()
        self.daemon_handlers = DaemonHandlers()
        self.osd_handlers = OSDHandlers()
        self.pool_handlers = PoolHandlers()

        # Initialize resources (auto-registers with FastMCP)
        self.health_resources = HealthResources(self.mcp, self.health_handlers)

        # Initialize tools (auto-registers with FastMCP)
        self.health_tools = HealthTools(self.mcp, self.health_handlers)
        self.host_tools = HostTools(self.mcp, self.host_handlers)
        self.daemon_tools = DaemonTools(self.mcp, self.daemon_handlers)
        self.osd_tools = OSDTools(self.mcp, self.osd_handlers)
        self.pool_tools = PoolTools(self.mcp, self.pool_handlers)

        self.logger.info(
            "Ceph MCP Server initialized with FastMCP architecture",
            server_name=settings.mcp_server_name,
            version=str(settings.mcp_server_version),
            host=settings.server_host,
            port=settings.server_port,
            ceph_url=settings.ceph_manager_url,
            handlers=["health", "host", "daemon", "osd", "pool"],
        )

    async def run(self, host: str, port: int) -> None:
        """
        Run the FastMCP server.

        Args:
            host: Host to bind the server to
            port: Port to bind the server to
        """
        try:
            # Run the FastMCP server
            await self.mcp.run_async(
                transport="streamable-http", host=host, port=port, path="/mcp"
            )

        except KeyboardInterrupt:
            self.logger.info("Shutting down Ceph MCP Server (keyboard interrupt)")
        except Exception as e:
            self.logger.error("Server error", error=str(e), exc_info=True)
            raise
        finally:
            self.logger.info("Ceph MCP Server stopped")


def main() -> None:
    """
    Main entry point for the Ceph MCP Server.

    This function sets up the server and starts the asyncio event loop.
    """
    server = CephMCPServer()
    asyncio.run(server.run(settings.server_host, settings.server_port))


if __name__ == "__main__":
    main()
