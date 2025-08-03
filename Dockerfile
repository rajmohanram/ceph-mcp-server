#Dockerfile.base
FROM python:3.13-slim

# Set env defaults; override at runtime or build time
ENV MCP_PACKAGE=
ENV MCP_EXTRA_ARGS=""
ENV MCP_LOG_LEVEL=INFO
ENV MCP_TRANSPORT=stdio
ENV MCP_PORT=3000
ENV MCP_HOST=0.0.0.0
ENV MCP_MOUNT=sse

COPY --from=ghcr.io/astral-sh/uv:0.7.21 /uv /uvx /bin/

WORKDIR /app

# Build base package into virtualenv
RUN uv venv .venv && \
    . /app/.venv/bin/activate && \
    uv sync --active

ENV PATH="/app/.venv/bin:$PATH"

COPY . .

ENTRYPOINT ["/app/entrypoint.sh"]