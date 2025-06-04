"""
Base Ceph API Client

This module contains the core HTTP communication and authentication logic.
Handles all communication with the Ceph Manager's REST API.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urljoin

import httpx
import structlog

from ceph_mcp.config.settings import get_ssl_context, settings


class CephAPIError(Exception):
    """
    Custom exception for Ceph API related errors.

    Distinguish between different types of errors and handle
    them appropriately throughout the application.
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_data: dict | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class CephAuthenticationError(CephAPIError):
    """Specific exception for authentication-related errors."""


class CephTokenManager:
    """
    Manages Ceph API authentication tokens including acquisition and renewal.

    This class handles the complexity of token-based authentication,
    including automatic token refresh when tokens expire.
    """

    def __init__(self, client_session: httpx.AsyncClient, base_url: str):
        self.logger = structlog.get_logger(__name__)
        self.session = client_session
        self.base_url = base_url
        self.token: str | None = None
        self.token_expires_at: datetime | None = None
        self.token_refresh_buffer = timedelta(minutes=5)  # Refresh 5 min before expiry

    def _token_needs_refresh(self) -> bool:
        """
        Check if the current token needs to be refreshed.
        """
        if not self.token or not self.token_expires_at:
            return True

        # Refresh token before it expires (with buffer time)
        refresh_time = self.token_expires_at - self.token_refresh_buffer
        return datetime.now() >= refresh_time

    async def _authenticate(self) -> None:
        """
        Authenticate with Ceph Manager API and obtain a bearer token.

        This method calls the /api/auth endpoint with username/password
        to get a JWT token for subsequent API calls.
        """
        auth_url = urljoin(self.base_url, "/api/auth")
        self.logger.info(
            "Authenticating with Ceph Manager API",
            auth_url=auth_url,
            username=settings.ceph_username,
        )

        # Prepare authentication payload
        auth_payload = {
            "username": settings.ceph_username,
            "password": settings.ceph_password.get_secret_value(),
        }

        try:
            response = await self.session.post(
                auth_url,
                json=auth_payload,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/vnd.ceph.api.v1.0+json",
                },
            )

            if response.status_code == 201:
                # Successful authentication
                self.logger.info("Authentication successful")
                auth_data = response.json()
                self.token = auth_data.get("token")

                if not self.token:
                    raise CephAuthenticationError(
                        "No token received from authentication endpoint"
                    )

                # Calculate token expiry time
                # Ceph tokens typically expire in 8 hours, but we'll check the response
                expires_in = auth_data.get("ttl", 28800)  # Default 8 hours in seconds
                self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)

                self.logger.debug(
                    "Successfully authenticated with Ceph API",
                    expires_at=self.token_expires_at.isoformat(),
                )

            elif response.status_code == 400:
                raise CephAuthenticationError("Invalid credentials provided")
            elif response.status_code == 401:
                raise CephAuthenticationError(
                    "Authentication failed - check username and password"
                )
            else:
                error_msg = f"Authentication failed with status {response.status_code}"
                try:
                    error_data = response.json()
                    if "detail" in error_data:
                        error_msg += f": {error_data['detail']}"
                except httpx.HTTPError:
                    pass
                raise CephAuthenticationError(error_msg)

        except httpx.RequestError as e:
            raise CephAuthenticationError(
                f"Network error during authentication: {str(e)}"
            ) from e

    async def get_token(self) -> str:
        """
        Get a valid authentication token, refreshing if necessary.

        This method ensures we always have a valid token for API requests,
        automatically handling token refresh when needed.
        """
        if self._token_needs_refresh():
            await self._authenticate()

        if not self.token:
            raise CephAuthenticationError("Failed to obtain authentication token")

        return self.token

    def get_auth_headers(self) -> dict[str, str]:
        """
        Get headers with current authentication token.
        """
        if not self.token:
            raise CephAuthenticationError("No authentication token available")

        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "User-Agent": f"{settings.mcp_server_name}/{settings.mcp_server_version}",
        }


class BaseCephClient:
    """
    Async HTTP client for interacting with Ceph Manager API.

    Encapsulates the complexity of making API calls, including
    authentication, error handling, retry logic, and response parsing.
    """

    def __init__(self) -> None:
        self.logger = structlog.get_logger(__name__)
        self.base_url = str(settings.ceph_manager_url)
        # These will be injected by CephClient
        self.session: httpx.AsyncClient | None = None
        self.token_manager: CephTokenManager | None = None

    async def __aenter__(self) -> "BaseCephClient":
        """
        Async context manager entry - no session creation here.
        Session and token manager are injected by CephClient.
        """
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object | None,
    ) -> None:
        """
        Async context manager exit - no cleanup here.
        CephClient handles session cleanup.
        """
        pass

    async def _make_request(
        self,
        endpoint: str,
        accept_header: str,
        method: str = "GET",
        params: dict | None = None,
        json_data: dict | None = None,
    ) -> Any:
        """
        Make an authenticated request to the Ceph Manager API.

        This method handles token management, retries, and error handling
        for all API communications.
        """
        if not self.session or not self.token_manager:
            raise CephAPIError(
                "Client not properly initialized. Use 'async with' context manager."
            )

        url = urljoin(self.base_url, str(endpoint))

        self.logger.info(
            "Making Ceph API request", endpoint=endpoint, method=method, params=params
        )

        # Implement retry logic for transient failures and token refresh
        for attempt in range(settings.max_retries):
            try:
                # Ensure we have a valid token (handles expiration automatically)
                await self.token_manager.get_token()
                headers = self.token_manager.get_auth_headers()
                headers["Accept"] = accept_header

                self.logger.debug(
                    "Making Ceph API request",
                    endpoint=endpoint,
                    method=method,
                    params=params,
                    attempt=attempt + 1,
                )

                response = await self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_data,
                    headers=headers,
                )

                # Handle different response status codes appropriately
                if response.status_code == 200:
                    return response.json()
                if response.status_code == 401:
                    raise CephAPIError(
                        "Authentication failed. Check username and password.",
                        status_code=response.status_code,
                    )
                if response.status_code == 403:
                    raise CephAPIError(
                        "Access forbidden. Check user permissions.",
                        status_code=response.status_code,
                    )
                if response.status_code == 404:
                    raise CephAPIError(
                        f"Endpoint not found: {endpoint}",
                        status_code=response.status_code,
                    )
                if response.status_code >= 500:
                    # Server errors might be transient, so we'll retry
                    if attempt < settings.max_retries - 1:
                        wait_time = 2**attempt  # Exponential backoff
                        self.logger.warning(
                            "Server error, retrying",
                            status_code=response.status_code,
                            attempt=attempt + 1,
                            wait_time=wait_time,
                        )
                        await asyncio.sleep(wait_time)
                        continue

                    raise CephAPIError(
                        f"Server error: {response.status_code}",
                        status_code=response.status_code,
                    )

                raise CephAPIError(
                    f"Unexpected response: {response.status_code}",
                    status_code=response.status_code,
                )

            except httpx.RequestError as e:
                if attempt < settings.max_retries - 1:
                    wait_time = 2**attempt
                    self.logger.warning(
                        "Request failed, retrying",
                        error=str(e),
                        attempt=attempt + 1,
                        wait_time=wait_time,
                    )
                    await asyncio.sleep(wait_time)
                    continue

                raise CephAPIError(
                    f"Request failed after {settings.max_retries} attempts: "
                    f"{str(e)}"
                ) from e

        # This should never be reached, but just in case
        raise CephAPIError(f"Request failed after {settings.max_retries} attempts")
