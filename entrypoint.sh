#!/bin/bash
set -e  # Crash fast and loud if anything fails

. .venv/bin/activate

exec uv run ceph-mcp-server