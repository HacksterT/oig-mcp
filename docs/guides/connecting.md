[Wiki](../../README.md) › Guides › Connecting

# Connecting

*How to connect an MCP host to the server: locally over stdio, or to the hosted endpoint over HTTP.*

## Choose a transport

| You want | Use | You need |
|---|---|---|
| The server on your own machine, in a desktop host | stdio | A clone of this repository, [uv](https://docs.astral.sh/uv/), and the data API settings in `.env` ([Configuration](../../README.md#configuration)) |
| The hosted server, from any host that can send a header | Streamable HTTP | A bearer token (testers receive one; judges can ask through the hackathon) |

Over stdio the host starts the server itself and no token is involved. Over HTTP every request carries `Authorization: Bearer <token>`.

## stdio

Every desktop host runs the same command; replace `/path/to/oig-mcp` with your clone.

```text
command: uv
args:    --directory /path/to/oig-mcp run oig-mcp
```

**Claude Desktop** (`claude_desktop_config.json`):

```json
{ "mcpServers": { "oig-mcp": { "command": "uv", "args": ["--directory", "/path/to/oig-mcp", "run", "oig-mcp"] } } }
```

**VS Code** (`.vscode/mcp.json`), then enable the tools in Copilot chat's agent mode:

```json
{ "servers": { "oig-mcp": { "type": "stdio", "command": "uv", "args": ["--directory", "/path/to/oig-mcp", "run", "oig-mcp"] } } }
```

**Cursor** (`~/.cursor/mcp.json`): the Claude Desktop entry above, unchanged.

**Grok** (xAI's terminal agent): `grok mcp add oig-mcp -- uv --directory /path/to/oig-mcp run oig-mcp`, then `grok mcp doctor oig-mcp`.

**Claude Code:** `claude mcp add oig-mcp -- uv --directory /path/to/oig-mcp run oig-mcp`.

**watsonx Orchestrate** runs the server as a local toolkit: [`deploy/ibm/local-mcp-toolkit/`](../../deploy/ibm/local-mcp-toolkit/README.md).

## Streamable HTTP

```text
URL:    https://mcp.troymd.com/mcp
Header: Authorization: Bearer YOUR_TOKEN
```

**Claude Code:**

```bash
claude mcp add --transport http oig-mcp https://mcp.troymd.com/mcp \
  --header "Authorization: Bearer YOUR_TOKEN"
```

**Grok:** `grok mcp add --transport http oig-http https://mcp.troymd.com/mcp --header "Authorization: Bearer YOUR_TOKEN"`.

**Hermes Agent** and other hosts with HTTP and custom headers: the URL and header above. Claude Desktop's custom connectors do not accept a static bearer token, so use stdio there.

Each token is personal; if one is exposed, it is replaced. The token also unlocks the live checks listed in [Verify it yourself](../evaluation/method.md#verify-it-yourself).

## Check the connection

Ask: "Check the OIG dataset status." The answer should give a data date of November 4, 2026. Then try:

- "Staff left medication carts unlocked in a hallway. Has OIG cited this?"
- "Help me prepare for the next inspection at the VA El Paso Healthcare System."
- "What has OIG found at the Columbia VA?" It matches three facilities, so the host should show a choice or ask which one ([Elicitation](../architecture/mcp-features.md#elicitation)).

## What to expect on the hosted endpoint

- **Do not enter patient information or anything nonpublic.** Questions pass through your AI provider, Cloudflare, and the hosting machine; the server holds only public OIG material.
- **What is recorded** through judging: your token's name, each tool call and its arguments, every request the server makes to the data API and what came back, and each tool's result. Your conversation with your model is not visible to the server. Records stay on the hosting machine, capped at about 1 GB.
- **Limits:** about two tool calls a second per token, with bursts to 30; listings are not counted. "Rate limit exceeded" clears within seconds. If many searches arrive at once, a tool may answer that the data API is busy; retry after about five seconds.
- **Downtime:** it runs on one computer, so it can go down, and it restarts for a few seconds when testers are added. A restart ends open sessions; hosts that follow the MCP specification start a new one.

## Reporting a problem

Send the question, the host and model, the answer, and what went wrong. What matters most: a report number, finding, or link that is wrong or does not exist; a claim the cited report does not support; a count or trend that looks wrong; a question it should have answered; errors, slow responses, or trouble connecting.

---

← [MCP features](../architecture/mcp-features.md) · [Wiki home](../../README.md) · [Tools](../guides/tools.md) →
