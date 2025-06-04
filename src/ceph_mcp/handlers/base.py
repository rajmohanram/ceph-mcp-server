"""
Base Handler for MCP Operations

This module provides the base functionality that all domain-specific
handlers inherit from, ensuring consistent behavior and error handling.
"""

from abc import ABC, abstractmethod
from typing import Any

import structlog

from ceph_mcp.api.base import CephAPIError, CephAuthenticationError
from ceph_mcp.api.client import CephClient
from ceph_mcp.models.base import MCPResponse


class BaseHandler(ABC):
    """
    Base class for all MCP request handlers.

    This class provides common functionality like logging, error handling,
    and response formatting that all handlers need.
    """

    def __init__(self, domain: str):
        """
        Initialize the base handler.

        Args:
            domain: The domain this handler is responsible for (health, hosts, etc.)
        """
        self.domain = domain
        self.logger = structlog.get_logger(f"{__name__}.{domain}")

    async def get_global_client(self) -> CephClient:
        """Get the global authenticated Ceph client."""
        # Import here to avoid circular imports
        from ceph_mcp.server import get_global_client

        return await get_global_client()

    @abstractmethod
    async def _handle_operation(
        self, operation: str, params: dict[str, Any]
    ) -> MCPResponse:
        """
        Handle the specific operation for this domain.

        This method must be implemented by each domain-specific handler.

        Args:
            operation: The operation to perform
            params: Operation parameters

        Returns:
            MCPResponse with the operation result
        """

    async def handle_request(
        self, operation: str, params: dict[str, Any]
    ) -> MCPResponse:
        """
        Main entry point for handling MCP requests.

        This method provides consistent error handling and logging for all operations.

        Args:
            operation: The specific operation to perform
            params: Parameters for the operation

        Returns:
            MCPResponse with the operation result
        """
        self.logger.info(
            "Processing MCP request",
            domain=self.domain,
            operation=operation,
            params=params,
        )

        try:
            # Call the specific handler method
            response = await self._handle_operation(operation, params)

            self.logger.info(
                "MCP request completed successfully",
                domain=self.domain,
                operation=operation,
                success=response.success,
            )

            return response

        except CephAuthenticationError as e:
            self.logger.error(
                "Authentication error during MCP request",
                domain=self.domain,
                operation=operation,
                error=str(e),
            )
            return MCPResponse.error_response(
                message=f"Authentication failed: {str(e)}",
                error_code="AUTHENTICATION_ERROR",
            )

        except CephAPIError as e:
            self.logger.error(
                "Ceph API error during MCP request",
                domain=self.domain,
                operation=operation,
                error=str(e),
                status_code=getattr(e, "status_code", None),
            )
            return MCPResponse.error_response(
                message=f"Ceph API error: {str(e)}", error_code="CEPH_API_ERROR"
            )

        except ValueError as e:
            self.logger.error(
                "Validation error during MCP request",
                domain=self.domain,
                operation=operation,
                error=str(e),
            )
            return MCPResponse.error_response(
                message=f"Invalid parameters: {str(e)}", error_code="VALIDATION_ERROR"
            )

        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error(
                "Unexpected error during MCP request",
                domain=self.domain,
                operation=operation,
                error=str(e),
                exc_info=True,
            )
            return MCPResponse.error_response(
                message=f"An unexpected error occurred: {str(e)}",
                error_code="INTERNAL_ERROR",
            )

    def validate_required_params(
        self, params: dict[str, Any], required_keys: list
    ) -> None:
        """
        Validate that required parameters are present.

        Args:
            params: Parameters to validate
            required_keys: List of required parameter names

        Raises:
            ValueError: If any required parameter is missing
        """
        if len(required_keys) == 0:
            return
        missing_keys = [
            key for key in required_keys if key not in params or params[key] is None
        ]
        if missing_keys:
            raise ValueError(f"Missing required parameters: {', '.join(missing_keys)}")

    def validate_param_type(
        self, params: dict[str, Any], key: str, expected_type: type
    ) -> None:
        """
        Validate that a parameter has the expected type.

        Args:
            params: Parameters to validate
            key: Parameter key to check
            expected_type: Expected type for the parameter

        Raises:
            ValueError: If parameter type doesn't match
        """
        if key in params and not isinstance(params[key], expected_type):
            raise ValueError(
                f"Parameter '{key}' must be of type {expected_type.__name__}"
            )

    def get_optional_param(
        self, params: dict[str, Any], key: str, default: Any = None
    ) -> Any:
        """
        Get an optional parameter with a default value.

        Args:
            params: Parameters dictionary
            key: Parameter key
            default: Default value if key is not present

        Returns:
            Parameter value or default
        """
        return params.get(key, default)

    def create_success_response(
        self, data: Any, message: str, **kwargs: dict[str, Any]
    ) -> MCPResponse:
        """
        Create a standardized success response.

        Args:
            data: Response data
            message: Success message
            **kwargs: Additional response fields

        Returns:
            MCPResponse for success
        """
        return MCPResponse.success_response(data=data, message=message, **kwargs)

    def create_error_response(
        self, message: str, error_code: str, **kwargs: dict[str, Any]
    ) -> MCPResponse:
        """
        Create a standardized error response.

        Args:
            message: Error message
            error_code: Error code
            **kwargs: Additional response fields

        Returns:
            MCPResponse for error
        """
        return MCPResponse.error_response(
            message=message, error_code=error_code, **kwargs
        )
