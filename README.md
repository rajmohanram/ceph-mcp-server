# Ceph MCP Server

A Model Context Protocol (MCP) server that enables AI assistants to interact with Ceph storage clusters through natural language. This server provides a bridge between AI tools and your Ceph infrastructure, making storage management more accessible and intuitive.

## 🚀 Features

- **Health Monitoring**: Get comprehensive cluster health status and diagnostics
- **Host Management**: Monitor and manage cluster hosts and their services
- **Detailed Analysis**: Access detailed health checks for troubleshooting
- **Secure Communication**: Authenticated access to Ceph Manager API
- **Structured Responses**: AI-friendly output formatting for clear communication
- **Async Architecture**: Non-blocking operations for better performance

## 📋 Prerequisites

- Python 3.11 or higher
- UV package manager
- Access to a Ceph cluster with Manager API enabled
- Valid Ceph credentials with appropriate permissions

## 🛠️ Installation

1. **Clone and setup the project:**
```bash
# Create the project directory
mkdir ceph-mcp-server
cd ceph-mcp-server

# Initialize UV project
uv init --python 3.11

# Add dependencies
uv add mcp httpx pydantic python-dotenv structlog asyncio-mqtt
uv add --dev pytest pytest-asyncio black isort mypy ruff
```

2. **Set up your environment:**
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your Ceph cluster details
nano .env
```

3. **Configure your Ceph connection:**
```bash
# .env file contents
CEPH_MANAGER_URL=https://192.16.0.31:8443
CEPH_USERNAME=admin
CEPH_PASSWORD=your_ceph_password
CEPH_SSL_VERIFY=false  # Set to true in production with proper certificates
```

## 🏃‍♂️ Quick Start

1. **Start the MCP server:**
```bash
uv run python -m ceph_mcp.server
```

2. **Test the connection:**
The server will log its startup and any connection issues. Look for messages indicating successful connection to your Ceph cluster.

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `CEPH_MANAGER_URL` | Ceph Manager API endpoint | `https://192.16.0.31:8443` | Yes |
| `CEPH_USERNAME` | Ceph username for API access | `admin` | Yes |
| `CEPH_PASSWORD` | Ceph password for authentication | - | Yes |
| `CEPH_SSL_VERIFY` | Enable SSL certificate verification | `true` | No |
| `CEPH_CERT_PATH` | Path to custom SSL certificate | - | No |
| `LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR) | `INFO` | No |
| `MAX_REQUESTS_PER_MINUTE` | Rate limiting for API requests | `60` | No |

### Security Considerations

- **Production Usage**: Always enable SSL verification (`CEPH_SSL_VERIFY=true`) in production
- **Credentials**: Store credentials securely and never commit them to version control
- **Network Access**: Ensure the MCP server can reach your Ceph Manager API endpoint
- **Permissions**: Use a dedicated Ceph user with minimal required permissions

## 🎯 Available Tools

The MCP server provides four main tools for AI assistants:

### 1. `get_cluster_health`
Get comprehensive cluster health status including overall health, warnings, and statistics.

**Use cases:**
- "How is my Ceph cluster doing?"
- "Are there any storage issues I should know about?"
- "What's the current status of my cluster?"

### 2. `get_host_status`
Retrieve information about all hosts in the cluster including online/offline status and service distribution.

**Use cases:**
- "Which hosts are online in my cluster?"
- "What services are running on each host?"
- "Are any hosts having problems?"

### 3. `get_health_details`
Get detailed health check information for troubleshooting specific issues.

**Use cases:**
- "What specific warnings does my cluster have?"
- "Give me detailed information about cluster errors"
- "Help me troubleshoot this storage issue"

### 4. `get_host_details`
Get comprehensive information about a specific host.

**Parameters:**
- `hostname`: The name of the host to examine

**Use cases:**
- "Tell me about host ceph-node-01"
- "What services are running on this specific host?"
- "Get detailed specs for this host"

## 📊 Example Interactions

### Health Check
```
AI Assistant: "How is my Ceph cluster doing?"

Response: ✅ Cluster is healthy. All 3 hosts are online. OSDs: 12/12 up.
🟢 Overall Status: HEALTH_OK
🖥️  Hosts: 3/3 online
💾 OSDs: 12/12 up
```

### Troubleshooting
```
AI Assistant: "What warnings does my cluster have?"

Response: 🟡 Cluster has 2 warning(s) requiring attention.
🟡 Warnings requiring attention:
   - OSD_NEARFULL: 1 osd(s) are getting full
   - POOL_BACKFILLFULL: 1 pool(s) are backfill full
```

## 🧪 Development

### Running Tests
```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=ceph_mcp

# Run specific test types
uv run pytest -m "not integration"  # Skip integration tests
```

### Code Quality
```bash
# Format code
uv run black src/ tests/
uv run isort src/ tests/

# Lint code
uv run ruff check src/ tests/
uv run mypy src/

# All checks
uv run ruff check src/ tests/ && uv run mypy src/ && uv run pytest
```

### Project Structure
```
ceph-mcp-server/
├── src/ceph_mcp/
│   ├── __init__.py          # Package initialization
│   ├── server.py            # Main MCP server
│   ├── api/
│   │   └── ceph_client.py   # Ceph API client
│   ├── config/
│   │   └── settings.py      # Configuration management
│   ├── handlers/
│   │   └── health_handlers.py # Request handlers
│   ├── models/
│   │   └── ceph_models.py   # Data models
│   └── utils/               # Utility functions
├── tests/                   # Test suite
├── .env.example            # Environment template
├── pyproject.toml          # Project configuration
└── README.md              # This file
```

## 🐛 Troubleshooting

### Common Issues

1. **Connection Refused**
   - Check if Ceph Manager is running and accessible
   - Verify the URL and port in your configuration
   - Ensure network connectivity between MCP server and Ceph cluster

2. **Authentication Failed**
   - Verify username and password are correct
   - Check that the user has appropriate permissions
   - Ensure the Ceph user account is active

3. **SSL Certificate Errors**
   - For development: Set `CEPH_SSL_VERIFY=false`
   - For production: Use proper SSL certificates or specify `CEPH_CERT_PATH`

4. **Permission Denied**
   - Ensure the Ceph user has read permissions for health and host information
   - Check Ceph user capabilities: `ceph auth get client.your-username`

### Debugging

Enable debug logging to get more detailed information:
```bash
LOG_LEVEL=DEBUG uv run python -m ceph_mcp.server
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and add tests
4. Run the test suite: `uv run pytest`
5. Format code: `uv run black src/ tests/`
6. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- [Ceph Storage](https://ceph.io/) - The distributed storage system
- [Model Context Protocol](https://modelcontextprotocol.io/) - The protocol enabling AI integration
- [Anthropic](https://anthropic.com/) - For developing MCP and Claude

## 📞 Support

- Create an issue for bug reports or feature requests
- Check existing issues before creating new ones
- Provide detailed information about your environment when reporting issues
