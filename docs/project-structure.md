# Updated Modular Project Structure

```
ceph-mcp-server/
├── src/ceph_mcp/
│   ├── __init__.py
│   ├── server.py                    # Main MCP server (updated to use new handlers)
│   │
│   ├── api/                         # API client modules
│   │   ├── __init__.py
│   │   ├── base.py                  # BaseCephClient + CephTokenManager
│   │   ├── client.py                # Main CephClient (combines all endpoints)
│   │   └── endpoints/               # Individual endpoint clients
│   │       ├── __init__.py
│   │       ├── health.py            # HealthClient
│   │       ├── hosts.py             # HostClient
│   │       ├── osds.py              # OSDClient
│   │       ├── pools.py             # PoolClient
│   │       ├── rbd.py               # RBDClient (future)
│   │       └── rgw.py               # RGWClient (future)
│   │
│   ├── handlers/                    # MCP request handlers
│   │   ├── __init__.py
│   │   ├── health_handlers.py       # Health-related handlers
│   │   ├── host_handlers.py         # Host-related handlers
│   │   ├── cluster_handlers.py      # Combined cluster operations
│   │   ├── osd_handlers.py          # OSD handlers (future)
│   │   └── pool_handlers.py         # Pool handlers (future)
│   │
│   ├── models/                      # Data models
│   │   ├── __init__.py
│   │   ├── ceph_models.py           # Core Ceph models
│   │   ├── health_models.py         # Health-specific models (future)
│   │   ├── host_models.py           # Host-specific models (future)
│   │   └── response_models.py       # MCP response models
│   │
│   ├── config/                      # Configuration
│   │   ├── __init__.py
│   │   └── settings.py              # Settings and configuration
│   │
│   └── utils/                       # Utility functions
│       ├── __init__.py
│       ├── logging.py               # Logging utilities
│       ├── validation.py            # Data validation helpers
│       └── formatters.py            # Response formatting utilities
│
├── tests/                           # Test suite
│   ├── __init__.py
│   ├── test_api/                    # API client tests
│   │   ├── test_base.py
│   │   ├── test_health_client.py
│   │   └── test_host_client.py
│   ├── test_handlers/               # Handler tests
│   │   ├── test_health_handlers.py
│   │   └── test_host_handlers.py
│   └── test_integration/            # Integration tests
│       └── test_full_workflow.py
│
├── .env.example
├── .env
├── pyproject.toml
├── run_server.py
└── README.md
```

## Benefits of This Modular Approach

### 1. **Separation of Concerns**
- **API Layer**: Pure HTTP communication and Ceph protocol handling
- **Handler Layer**: MCP protocol and business logic
- **Model Layer**: Data validation and transformation
- **Each module has a single responsibility**

### 2. **Easy Expansion**
Adding new Ceph APIs is straightforward:

```python
# Just add a new endpoint client
class RGWClient(BaseCephClient):
    async def get_buckets(self): ...
    async def create_bucket(self): ...

# Add corresponding handlers
class RGWHandlers:
    async def list_buckets(self): ...
    async def create_bucket(self): ...

# Register in main client
class CephClient:
    def __init__(self):
        self.rgw = RGWClient()  # Add this line
```

### 3. **Independent Testing**
Each component can be tested in isolation:

```python
# Test just the health client
async def test_health_client():
    async with HealthClient() as client:
        health = await client.get_cluster_health()
        assert health.status in [HealthStatus.OK, HealthStatus.WARN, HealthStatus.ERR]

# Test just the handler logic with mocked client
async def test_health_handler():
    with patch('ceph_mcp.handlers.health_handlers.CephClient') as mock_client:
        # Test handler logic without real API calls
```

### 4. **Better Error Handling**
Errors can be handled at the appropriate level:

```python
# API-level errors (network, auth, HTTP)
class BaseCephClient:
    async def _make_request(self): ...

# Endpoint-specific errors (data parsing, validation)
class HealthClient:
    async def get_cluster_health(self): ...

# Business logic errors (missing parameters, invalid combinations)
class HealthHandlers:
    async def get_cluster_health_summary(self): ...
```

### 5. **Flexible Usage Patterns**

```python
# Use individual clients for specific operations
async with HealthClient() as health_client:
    health = await health_client.get_cluster_health()

# Use combined client for complex operations
async with CephClient() as client:
    status = await client.get_cluster_status()  # Uses multiple endpoints

# Use handlers for MCP protocol responses
handler = HealthHandlers()
response = await handler.get_cluster_health_summary({})
```

## Migration Strategy

To migrate your current code to this structure:

### Phase 1: Extract Base Client
1. Move authentication logic to `BaseCephClient`
2. Move `_make_request` to base class
3. Update existing code to inherit from base

### Phase 2: Split Endpoints
1. Create `HealthClient` with health methods
2. Create `HostClient` with host methods
3. Update handlers to use specific clients

### Phase 3: Add Combined Client
1. Create main `CephClient` that orchestrates endpoint clients
2. Add convenience methods for common combinations
3. Update handlers to use main client

### Phase 4: Expand
1. Add new endpoint clients (OSDs, Pools, etc.)
2. Add corresponding handlers
3. Register new tools in MCP server

## Example Usage in Updated Server

```python
# server.py - Updated to use modular handlers
class CephMCPServer:
    def __init__(self):
        # Initialize all handler types
        self.health_handlers = HealthHandlers()
        self.host_handlers = HostHandlers()
        self.cluster_handlers = ClusterHandlers()
        self.osd_handlers = OSDHandlers()        # Future
        self.pool_handlers = PoolHandlers()      # Future

    @self.server.call_tool()
    async def call_tool(name: str, arguments: dict):
        # Route to appropriate handler based on operation type
        if name == "get_cluster_health":
            return await self.health_handlers.get_cluster_health_summary(arguments)
        elif name == "get_host_status":
            return await self.host_handlers.get_host_status(arguments)
        elif name == "get_cluster_overview":
            return await self.cluster_handlers.get_cluster_overview(arguments)
        # ... more routing
```

This modular approach scales much better and makes your codebase maintainable as you add more Ceph functionality!


Summary: Why Modular Architecture is Better
Your instinct to make the code more modular is absolutely correct! Here are the key advantages:
🎯 Single Responsibility

HealthClient only handles health endpoints
HostClient only handles host endpoints
BaseCephClient only handles HTTP communication
Each class has one reason to change

🔧 Easy Maintenance

Bug in health API? Only touch HealthClient
New authentication method? Only change BaseCephClient
New host endpoint? Only modify HostClient

📈 Better Scalability

Adding new endpoints doesn't bloat existing classes
Each new API area gets its own focused client
Combined operations remain optional convenience methods

🧪 Improved Testing

Test individual endpoint clients in isolation
Mock specific clients without affecting others
Unit test business logic separately from API communication

🔀 Flexible Usage
python# Light usage - just what you need
async with HealthClient() as client:
    health = await client.get_cluster_health()

# Heavy usage - full orchestration
async with CephClient() as client:
    overview = await client.get_cluster_status()
👥 Team Development

Different developers can work on different endpoint clients
Clear boundaries between different API areas
Easier code reviews focused on specific functionality

The modular approach transforms your monolithic CephClient into a well-organized ecosystem of focused, single-purpose clients that can work independently or together. This is exactly the kind of architecture that scales well as your MCP server grows to support more Ceph functionality.

