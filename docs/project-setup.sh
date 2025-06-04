#!/bin/bash
# This script sets up the project directory structure and initializes a Git repository.

# Create the project directory
mkdir ceph-mcp-server
cd ceph-mcp-server

# Initialize UV project with Python 3.11+
uv init --python 3.11

# Add core MCP dependencies
uv add mcp

# Add HTTP client and async support
uv add httpx asyncio-mqtt

# Add development dependencies
uv add --dev pytest pytest-asyncio black isort mypy

# Add configuration management
uv add pydantic pydantic-settings pydantic-extra-types python-dotenv

# Add logging and monitoring
uv add structlog

# Create the basic project structure
mkdir -p src/ceph_mcp/{api,models,handlers,utils,config}
touch src/ceph_mcp/__init__.py
touch src/ceph_mcp/api/__init__.py
touch src/ceph_mcp/models/__init__.py
touch src/ceph_mcp/handlers/__init__.py
touch src/ceph_mcp/utils/__init__.py
touch src/ceph_mcp/config/__init__.py

# Create main entry point
touch src/ceph_mcp/server.py

# Create configuration files
touch .env.example
touch pyproject.toml.extra
