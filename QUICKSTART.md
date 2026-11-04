# Quickstart

From a clone to a running server connected to an MCP client.

## 1. Install and configure

Requires [uv](https://docs.astral.sh/uv/).

```bash
cp .env.example .env
uv sync
```

Set `OIG_DATA_API_BASE_URL` in `.env` to the OIG data API. The default points at a local instance from the `oig-data-source` repository. For the hosted API, also set `CF_ACCESS_CLIENT_ID` and `CF_ACCESS_CLIENT_SECRET`.

## 2. Run over stdio

```bash
uv run oig-mcp
```

The server waits silently on stdin and stdout; MCP clients launch it as a subprocess. Press Ctrl-C to stop.

## 3. Connect a client

Claude Code (`.mcp.json`) or Claude Desktop (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "oig-mcp": {
      "command": "uv",
      "args": ["run", "oig-mcp"],
      "cwd": "/absolute/path/to/oig-mcp"
    }
  }
}
```

Then ask: "Read vaoig://about, then check the OIG dataset status." The resource works on its own. The status tool needs the data API; without it the tool returns an error with a hint.

## 4. Run over HTTP

```bash
export MCP_AUTH_TOKEN=$(openssl rand -hex 32)
MCP_TRANSPORT=streamable-http uv run oig-mcp
curl http://localhost:8000/health
```

The MCP endpoint is `http://localhost:8000/mcp`, and callers must send `Authorization: Bearer <MCP_AUTH_TOKEN>`. The server will not start over HTTP without a token. In a container or on IBM Code Engine, a platform-set `PORT` switches the server to HTTP automatically.

## 5. Verify

```bash
uv sync --group dev
uv run pytest tests/ -v
uv run ruff check . && uv run ruff format --check .
```
