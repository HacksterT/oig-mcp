# Deployment

The server runs two ways:

| Where | Transport | How |
|---|---|---|
| IBM watsonx Orchestrate, the hackathon deployment | stdio, inside Orchestrate's runtime | A local toolkit. Orchestrate runs the server and passes it the data API's settings from a key_value connection. See [`ibm/local-mcp-toolkit/README.md`](ibm/local-mcp-toolkit/README.md) |
| A hosted HTTP endpoint, for testers, judges, and any MCP client | Streamable HTTP behind Cloudflare and bearer tokens | The container image, described below |

IBM Code Engine was planned as the Orchestrate route and not used: the hackathon account had no resource group or registry namespace for it. The image would run there unchanged.

## The hosted HTTP server

```
MCP client  -- HTTPS, Authorization: Bearer <token>             -->  oig-mcp container
oig-mcp     -- HTTPS, Cloudflare Access service token + API key -->  OIG data API
```

| Item | Value |
|---|---|
| Image | Root `Dockerfile`. Dependencies are installed from `uv.lock`, and it runs as non-root |
| Port | `8080`. The image sets `PORT`, as container platforms do, which switches the server to HTTP |
| MCP endpoint | `/mcp`. Streamable HTTP with a session per client and streamed (SSE) replies, so the server can ask the user mid-call on any protocol version. Idle sessions close after 30 minutes |
| Health and version | `/health` and `/version`. Open, and they return no data. There is no `/ping` |
| Rate limits | 2 requests a second per token, burst 30, counting every MCP request. Kept in memory per instance, so N instances allow up to N times that |

| Setting | Secret | Value |
|---|---|---|
| `MCP_AUTH_TOKEN` | Yes | New for each deployment: `openssl rand -hex 32`. The server refuses to start without it |
| `CF_ACCESS_CLIENT_ID` | Yes | Troy provides it |
| `CF_ACCESS_CLIENT_SECRET` | Yes | Troy provides it |
| `OIG_DATA_API_KEY` | Yes | Troy provides it. The data API's own key behind Access; never print it |
| `OIG_DATA_API_BASE_URL` | No, but keep it out of the repository | Troy provides it |
| `STALE_AFTER_DAYS` | No | `30` |

## Check a build

```bash
deploy/verify_image.sh
```

This builds the image with docker or podman, then checks it: no secrets in the image, it refuses to start unsafely, a missing or wrong Cloudflare token gives a clean refusal, and with good credentials everything in the next command passes. It needs the settings above in the environment or `.env`, including `OIG_DATA_API_KEY` now that the data API requires it.

## Check a running server

```bash
uv run python deploy/verify_deployment.py --url https://<APP_URL>
```

This tests both connections from outside: who may reach `/mcp`, and whether tools get live data through the API. It needs `MCP_AUTH_TOKEN`. With the API URL and Cloudflare token set too, it also tests the API directly. Without them, it skips that part and says so.

Then check how it holds up under hostile and heavy input:

```bash
uv run python deploy/robustness_check.py --url https://<APP_URL>
```

It sends every tool path traversal, header and query injection, SQL and search syntax, and values past every bound, then bursts past the rate limit and the data API's search slots, and checks that every reply is a clean answer or error with no stack trace, upstream address, or credential. No model is involved. It needs `MCP_AUTH_TOKEN`, and takes about a minute.

## Add or remove a tester

Each tester gets a named token, so one can be removed without affecting the rest. Run these on the machine serving `/mcp`, from this repo. `add` creates the token, writes it to `MCP_CLIENT_TOKENS` in `.env`, restarts the server, and prints only the token, so pipe it to the clipboard rather than the screen:

```bash
python3 deploy/mcp_clients.py add <name> | pbcopy
python3 deploy/mcp_clients.py list
python3 deploy/mcp_clients.py remove <name>
```

Names are lowercase letters, digits, `-`, and `_`. Each change restarts the server for a few seconds. To replace an exposed token, `remove` and then `add`. Send the tester [docs/testers.md](../docs/testers.md) and the token, and paste the token before copying anything else.

## Run it locally for any MCP client

```bash
docker compose up -d --build
```

The endpoint is `http://127.0.0.1:8000/mcp`, using the same image. Only the settings above reach the container, so an evaluation key in `.env` stays out of it.
