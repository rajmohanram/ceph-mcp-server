"""
Base Models for Ceph MCP Server

This module contains common base models and response structures used
across all domain-specific models.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class BaseComponentInfo(BaseModel):
    """
    Base model for Ceph component information.

    This provides common fields and methods that most Ceph components share.
    """

    name: str = Field(..., description="Component name/identifier")
    status: Any = Field(None, description="Component status")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="When this information was collected"
    )

    def is_healthy(self) -> bool:
        """Check if this component is in a healthy state."""
        healthy_statuses = ["up", "online", "active", "ok"]
        return str(self.status).lower() in healthy_statuses

    def get_status_summary(self) -> str:
        """Get a human-readable summary of this component's status."""
        status_emoji = "🟢" if self.is_healthy() else "🔴"
        return f"{status_emoji} {self.name}: {self.status}"


class MCPResponse(BaseModel):
    """
    Standardized response format for MCP operations.

    Ensures all responses from MCP server have a consistent structure,
    making it easier for AI assistants to parse and present information.
    """

    success: bool = Field(..., description="Whether the operation was successful")
    data: Any | None = Field(None, description="Response data")
    message: str = Field(..., description="Human-readable message about the operation")
    error_code: str | None = Field(None, description="Error code if operation failed")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="When this response was generated"
    )

    @classmethod
    def success_response(
        cls, data: Any, message: str = "Operation completed successfully"
    ) -> "MCPResponse":
        """Create a successful response."""
        return cls(success=True, data=data, message=message, error_code=None)

    @classmethod
    def error_response(
        cls, message: str, error_code: str | None = None
    ) -> "MCPResponse":
        """Create an error response."""
        return cls(success=False, data=None, message=message, error_code=error_code)
