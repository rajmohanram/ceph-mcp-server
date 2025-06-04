"""
Module to run the Ceph MCP server.
"""

import asyncio

from ceph_mcp.server import CephMCPServer


async def main() -> None:
    """
    Main entry point to start the Ceph MCP server.
    This function initializes the server and starts listening for requests.
    """
    server = CephMCPServer()
    await server.run()


asyncio.run(main())
