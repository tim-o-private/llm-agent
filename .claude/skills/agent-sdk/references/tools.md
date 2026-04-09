# Custom Tools & MCP Servers

## Custom Tools (In-Process)

Define Python functions as tools, wrap in an SDK MCP server that runs in your process.

### Basic tool

```python
from typing import Any
from claude_agent_sdk import tool, create_sdk_mcp_server

@tool(
    "get_temperature",
    "Get current temperature at a location",
    {"latitude": float, "longitude": float},
)
async def get_temperature(args: dict[str, Any]) -> dict[str, Any]:
    # ... fetch from API ...
    return {"content": [{"type": "text", "text": f"Temperature: {temp}F"}]}

weather_server = create_sdk_mcp_server(
    name="weather", version="1.0.0", tools=[get_temperature],
)

options = ClaudeAgentOptions(
    mcp_servers={"weather": weather_server},
    allowed_tools=["mcp__weather__get_temperature"],
)
```

### Tool naming convention

`mcp__{server_name}__{tool_name}` — e.g. `mcp__weather__get_temperature`.

Wildcard: `"mcp__weather__*"` allows all tools from a server.

### Input schema formats

**Simple dict** — all keys required:
```python
{"latitude": float, "longitude": float}
```

**Full JSON Schema** — for enums, optional fields, nested objects:
```python
{
    "type": "object",
    "properties": {
        "unit_type": {"type": "string", "enum": ["length", "temperature"]},
        "value": {"type": "number"},
    },
    "required": ["unit_type", "value"],
}
```

**Optional parameters** — leave out of schema, mention in description, read with `args.get()`:
```python
@tool(
    "search",
    "Search with optional limit (1-100).",
    {"query": str},
)
async def search(args: dict[str, Any]) -> dict[str, Any]:
    limit = args.get("limit", 10)
    ...
```

### Error handling

Return `{"is_error": True}` to signal failure without killing the loop:

```python
@tool("fetch_data", "Fetch from API", {"endpoint": str})
async def fetch_data(args: dict[str, Any]) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(args["endpoint"])
            if response.status_code != 200:
                return {
                    "content": [{"type": "text", "text": f"API error: {response.status_code}"}],
                    "is_error": True,
                }
            return {"content": [{"type": "text", "text": response.text}]}
    except Exception as e:
        return {
            "content": [{"type": "text", "text": f"Failed: {str(e)}"}],
            "is_error": True,
        }
```

**Uncaught exceptions kill the agent loop.** Always catch inside the handler.

### Tool annotations

```python
from claude_agent_sdk import ToolAnnotations

@tool("my_tool", "...", {...}, annotations=ToolAnnotations(readOnlyHint=True))
```

| Field | Default | Meaning |
|-------|---------|---------|
| `readOnlyHint` | `False` | Enables parallel execution with other read-only tools |
| `destructiveHint` | `True` | May perform destructive updates (informational) |
| `idempotentHint` | `False` | Repeated calls = no additional effect (informational) |
| `openWorldHint` | `True` | Reaches systems outside your process (informational) |

### Returning images

```python
import base64

@tool("fetch_image", "Fetch an image", {"url": str})
async def fetch_image(args):
    async with httpx.AsyncClient() as client:
        response = await client.get(args["url"])
    return {
        "content": [{
            "type": "image",
            "data": base64.b64encode(response.content).decode("ascii"),
            "mimeType": response.headers.get("content-type", "image/png"),
        }]
    }
```

### Multiple tools on one server

```python
server = create_sdk_mcp_server(
    name="weather", version="1.0.0",
    tools=[get_temperature, get_precipitation, get_forecast],
)
options = ClaudeAgentOptions(
    mcp_servers={"weather": server},
    allowed_tools=["mcp__weather__*"],
)
```

## External MCP Servers

### stdio (local process)

```python
options = ClaudeAgentOptions(
    mcp_servers={
        "github": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-github"],
            "env": {"GITHUB_TOKEN": os.environ["GITHUB_TOKEN"]},
        }
    },
    allowed_tools=["mcp__github__*"],
)
```

### HTTP/SSE (remote)

```python
options = ClaudeAgentOptions(
    mcp_servers={
        "remote-api": {
            "type": "sse",  # or "http" for non-streaming
            "url": "https://api.example.com/mcp/sse",
            "headers": {"Authorization": f"Bearer {token}"},
        }
    },
)
```

### From `.mcp.json`

Load via `setting_sources=["project"]`. File format:

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": { "GITHUB_TOKEN": "${GITHUB_TOKEN}" }
    }
  }
}
```

### Verify connection

```python
if isinstance(message, SystemMessage) and message.subtype == "init":
    for server in message.data.get("mcp_servers", []):
        if server.get("status") != "connected":
            print(f"Server {server['name']} failed to connect")
```

## Built-in Tools

| Tool | What it does |
|------|-------------|
| `Read` | Read files |
| `Write` | Create new files |
| `Edit` | Precise edits to existing files |
| `Bash` | Terminal commands, scripts, git |
| `Glob` | Find files by pattern |
| `Grep` | Search file contents with regex |
| `WebSearch` | Search the web |
| `WebFetch` | Fetch and parse web pages |
| `Agent` | Spawn subagents |
| `Skill` | Invoke skills |
| `AskUserQuestion` | Ask user clarifying questions |
| `ToolSearch` | Dynamically find/load tools on-demand |

Use the `tools` option to restrict which built-ins are in context (reduces token cost). Use `allowed_tools` to pre-approve specific ones.
