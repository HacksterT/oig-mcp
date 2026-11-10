# Deployment

The target is IBM Code Engine, registered as a remote MCP toolkit in watsonx Orchestrate. Start with [the handoff to Bob](../docs/handoff/2026-11-04-troy-bob-deployment-handoff.md), which lists what is tested and what is assumed.

```
watsonx Orchestrate  -- HTTPS, Authorization: Bearer MCP_AUTH_TOKEN -->  oig-mcp on Code Engine
oig-mcp              -- HTTPS, Cloudflare Access service token      -->  OIG data API
```

| Item | Value |
|---|---|
| Image | Root `Dockerfile`. Dependencies are installed from `uv.lock`, and it runs as non-root |
| Port | `8080`. Code Engine sets `PORT`, which switches the server to HTTP |
| MCP endpoint | `/mcp`. Streamable HTTP, stateless, plain JSON responses. No SSE |
| Health and version | `/health` and `/version`. Open, and they return no data. There is no `/ping` |
| Rate limits | 2 requests a second per token, burst 30, counting every MCP request. Kept in memory per instance, so N instances allow up to N times that |

| Setting | Secret | Value |
|---|---|---|
| `MCP_AUTH_TOKEN` | Yes | New for IBM: `openssl rand -hex 32`. The server refuses to start without it |
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
