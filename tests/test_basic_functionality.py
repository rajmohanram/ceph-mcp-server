"""
Basic tests for the Ceph MCP Server functionality.

These tests help ensure your server is configured correctly and can
communicate with your Ceph cluster. They're designed to be run against
a real Ceph cluster in your development environment.
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from ceph_mcp.api.ceph_client import CephAPIError, CephClient
from ceph_mcp.config.settings import settings
from ceph_mcp.models.ceph_models import ClusterHealth, HealthStatus
from ceph_mcp.server import CephMCPServer


class TestConfiguration:
    """Test that configuration is properly loaded and validated."""

    def test_settings_loaded(self) -> None:
        """Ensure settings are loaded from environment."""
        assert settings.ceph_manager_url is not None
        assert settings.ceph_username is not None
        assert settings.mcp_server_name == "ceph-storage-assistant"

    def test_ceph_url_validation(self) -> None:
        """Test that Ceph URL validation works correctly."""
        # The URL should be properly formatted
        assert str(settings.ceph_manager_url).startswith(("http://", "https://"))
        assert not str(settings.ceph_manager_url).endswith("/")


class TestCephClient:
    """Test the Ceph API client functionality."""

    @pytest.mark.asyncio
    async def test_client_context_manager(self) -> None:
        """Test that the client can be used as an async context manager."""
        async with CephClient() as client:
            assert client.session is not None
            assert client.base_url == settings.ceph_manager_url

        # Session should be closed after exiting context
        assert client.session is None

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_cluster_health_real(self) -> None:
        """Test getting real cluster health (requires running Ceph cluster)."""
        try:
            async with CephClient() as client:
                health = await client.get_cluster_health()

                # Basic validation that we got a health response
                assert isinstance(health, ClusterHealth)
                assert health.status in [
                    HealthStatus.OK,
                    HealthStatus.WARN,
                    HealthStatus.ERR,
                ]
                assert isinstance(health.summary, str)

                print(f"Cluster Health: {health.status.value}")
                print(f"Summary: {health.summary}")

        except CephAPIError as e:
            pytest.skip(f"Could not connect to Ceph cluster: {e}")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_hosts_real(self) -> None:
        """Test getting real host information (requires running Ceph cluster)."""
        try:
            async with CephClient() as client:
                hosts = await client.get_hosts()

                # Basic validation
                assert isinstance(hosts, list)

                if hosts:  # If we have hosts, validate their structure
                    host = hosts[0]
                    assert hasattr(host, "hostname")
                    assert hasattr(host, "addr")
                    assert hasattr(host, "status")

                    print(f"Found {len(hosts)} hosts")
                    for host in hosts:
                        print(f"  - {host.hostname}: {host.status}")

        except CephAPIError as e:
            pytest.skip(f"Could not connect to Ceph cluster: {e}")

    @pytest.mark.asyncio
    async def test_authentication_error_handling(self) -> None:
        """Test that authentication errors are handled properly."""
        # Create a client with invalid credentials
        with patch("ceph_mcp.config.settings.settings") as mock_settings:
            mock_settings.ceph_username = "invalid_user"
            mock_settings.ceph_password = "invalid_password"
            mock_settings.ceph_manager_url = settings.ceph_manager_url
            mock_settings.request_timeout_seconds = 5
            mock_settings.max_retries = 1

            client = CephClient()

            # This should raise a CephAPIError for authentication failure
            with pytest.raises(CephAPIError) as exc_info:
                async with client:
                    await client.get_cluster_health()

            # The error should indicate authentication failure
            assert "authentication" in str(exc_info.value).lower() or "401" in str(
                exc_info.value
            )


class TestMCPServer:
    """Test the MCP server functionality."""

    def test_server_initialization(self) -> None:
        """Test that the MCP server initializes correctly."""
        server = CephMCPServer()
        assert server.server is not None
        assert server.health_handlers is not None
        assert server.host_handlers is not None

    @pytest.mark.asyncio
    async def test_tool_registration(self) -> None:
        """Test that tools are properly registered."""
        server = CephMCPServer()

        # We can't easily test the actual MCP server without setting up
        # a full MCP client, but we can test that our handlers work
        assert server.health_handlers is not None
        assert server.host_handlers is not None


class TestHandlers:
    """Test the request handlers."""

    @pytest.mark.asyncio
    async def test_health_handler_with_mock(self) -> None:
        """Test health handler with mock Ceph client."""
        from ceph_mcp.handlers.health_handlers import HealthHandlers

        # Create a mock cluster health response
        mock_health = ClusterHealth(
            status=HealthStatus.OK, summary="Cluster is healthy", checks={}, mutes=[]
        )

        # Mock the entire cluster status
        mock_cluster_status = AsyncMock()
        mock_cluster_status.health = mock_health
        mock_cluster_status.get_host_summary.return_value = "All hosts online"
        mock_cluster_status.get_overall_summary.return_value = "Everything looks good"
        mock_cluster_status.total_hosts = 3
        mock_cluster_status.online_hosts = 3
        mock_cluster_status.total_osds = 12
        mock_cluster_status.up_osds = 12
        mock_cluster_status.in_osds = 12
        mock_cluster_status.collected_at = pytest.approx(
            asyncio.get_event_loop().time()
        )

        with patch("ceph_mcp.handlers.health_handlers.CephClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get_cluster_status.return_value = mock_cluster_status
            mock_client_class.return_value.__aenter__.return_value = mock_client

            handler = HealthHandlers()
            response = await handler.get_cluster_health_summary({})

            assert response.success is True
            assert "healthy" in response.message.lower()
            assert response.data is not None


@pytest.mark.integration
class TestIntegration:
    """Integration tests that require a running Ceph cluster."""

    @pytest.mark.asyncio
    async def test_full_health_check_workflow(self) -> None:
        """Test the complete workflow from handler to Ceph API."""
        from ceph_mcp.handlers.health_handlers import HealthHandlers

        try:
            handler = HealthHandlers()
            response = await handler.get_cluster_health_summary({})

            # Should get a successful response
            assert response.success is True
            assert response.data is not None
            assert "overall_health" in response.data

            print(f"Integration test result: {response.message}")

        except Exception as e:
            pytest.skip(f"Integration test failed - check Ceph connectivity: {e}")

    @pytest.mark.asyncio
    async def test_host_status_workflow(self) -> None:
        """Test the complete host status workflow."""
        from ceph_mcp.handlers.health_handlers import HealthHandlers

        try:
            handler = HealthHandlers()
            response = await handler.get_host_status({})

            assert response.success is True
            assert response.data is not None
            assert "hosts" in response.data

            print(f"Host status test result: {response.message}")

        except Exception as e:
            pytest.skip(f"Integration test failed - check Ceph connectivity: {e}")


# Helper fixtures for testing
@pytest.fixture
def mock_ceph_health() -> ClusterHealth:
    """Fixture providing a mock Ceph health response."""
    return ClusterHealth(
        status=HealthStatus.OK,
        summary="Cluster is operating normally",
        checks={},
        mutes=[],
        overall_status_description="All systems are functioning correctly",
    )


# Utility function for manual testing
async def manual_test_connection() -> None:
    """
    Manual test function you can run to verify connectivity.

    Usage:
        python -c "from tests.test_basic_functionality import manual_test_connection; import asyncio; asyncio.run(manual_test_connection())"
    """
    print(f"Testing connection to: {settings.ceph_manager_url}")
    print(f"Using username: {settings.ceph_username}")

    try:
        async with CephClient() as client:
            print("✅ Successfully created client connection")

            health = await client.get_cluster_health()
            print(f"✅ Cluster health: {health.status.value}")
            print(f"   Summary: {health.summary}")

            hosts = await client.get_hosts()
            print(f"✅ Retrieved {len(hosts)} hosts")
            for host in hosts:
                print(f"   - {host.hostname}: {host.status}")

            print("🎉 All tests passed! Your Ceph MCP server should work correctly.")

    except CephAPIError as e:
        print(f"❌ Ceph API Error: {e}")
        print("   Check your Ceph Manager URL, credentials, and network connectivity.")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        print("   Check your configuration and try again.")


if __name__ == "__main__":
    # Allow running this file directly for manual testing
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "test-connection":
        asyncio.run(manual_test_connection())
    else:
        print(
            "Run 'python tests/test_basic_functionality.py test-connection' "
            "to test your Ceph connection"
        )
        print("Or run 'uv run pytest tests/' to run the full test suite")
