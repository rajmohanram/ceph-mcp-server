"""
Ceph MCP Server Configuration Settings
This module defines the configuration settings for the Ceph MCP Server
using Pydantic.
"""

from enum import Enum

from pydantic import FilePath, HttpUrl, SecretStr, field_validator
from pydantic_extra_types.semantic_version import SemanticVersion as semver
from pydantic_settings import BaseSettings, SettingsConfigDict


# Define a custom Enum for log levels to ensure type safety
class LogLevel(str, Enum):
    """Enumeration for log levels to ensure type safety."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class CephMCPSettings(BaseSettings):
    """
    Centralized configuration for the Ceph MCP Server.

    This class uses Pydantic Settings to automatically load and validate
    configuration from environment variables, providing type safety and clear
    error messages if something is misconfigured.
    """

    # Ceph Manager API Configuration
    ceph_manager_url: HttpUrl
    ceph_username: str
    ceph_password: SecretStr
    ceph_ssl_verify: bool = True
    ceph_cert_path: FilePath | None = None

    @field_validator("ceph_cert_path", mode="before")
    @classmethod
    def empty_str_to_none(cls, v: str | None) -> str | None:
        """
        Convert empty strings to None for file paths.

        This is useful for optional file paths that may not be set.
        """
        if v == "" or v is None:
            return None
        return v

    # MCP Server Identity
    server_host: str = "0.0.0.0"
    server_port: int = 8000
    mcp_server_name: str = "ceph-storage-assistant"
    mcp_server_version: semver

    # Operational Settings
    log_level: LogLevel = LogLevel.INFO
    log_format: str = "json"
    max_requests_per_minute: int = 60
    cache_ttl_seconds: int = 30

    # Ceph client HTTP connection Settings
    request_timeout_seconds: int = 5
    max_retries: int = 3

    # Pydantic Settings configuration
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )


# Global settings instance that can be imported
# throughout the application
settings = CephMCPSettings()  # type: ignore[call-arg]


def get_ssl_context() -> bool | str:
    """
    Configure SSL context for HTTP requests to Ceph.

    This function handles the complexity of SSL configuration, including
    development scenarios where you might need to disable certificate
    verification.
    """
    if not settings.ceph_ssl_verify:
        # In development, need this for self-signed certificates
        return False
    if settings.ceph_cert_path:
        # Use custom certificate if provided
        return str(settings.ceph_cert_path)
    # Use system default certificate validation
    return True
