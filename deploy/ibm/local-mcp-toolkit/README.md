# watsonx Orchestrate: local (stdio) toolkit

This is how oig-mcp runs in watsonx Orchestrate. Orchestrate uploads a copy of the server, installs its dependencies, and starts `python server.py` over stdio inside its own runtime for each tool call. There is no container, Code Engine app, or public `/mcp` address. Adapted from the hackathon template's [`deploy/ibm/local-mcp-toolkit`](https://github.com/GSA-TTS/mcp-hackathon-template/tree/main/deploy/ibm/local-mcp-toolkit).

The server needs four values to reach the data API. They live in a **key_value** connection, `oig_mcp_data_TES`, and Orchestrate passes each one to the server as an environment variable:

| Variable | What it is |
|---|---|
| `OIG_DATA_API_BASE_URL` | The data API's https address, ending in `/v1/` |
| `CF_ACCESS_CLIENT_ID`, `CF_ACCESS_CLIENT_SECRET` | The Cloudflare Access service token |
| `OIG_DATA_API_KEY` | The data API's own key |

`MCP_AUTH_TOKEN` is not used: over stdio, Orchestrate starts the server itself, and nothing reaches it over the network.

## Register

With the ADK installed (`uv tool install ibm-watsonx-orchestrate`) and the four values in the repository's `.env`:

```bash
bash deploy/ibm/local-mcp-toolkit/register-toolkit.sh
```

The script reads the Orchestrate instance URL and API key from `WXO_INSTANCE_URL` and `WXO_API_KEY`, or from `IBM_URL` and `IBM_API_KEY` in `.env`, and prompts for the key if neither is set. It prints no secret. It stages `src/oig_mcp` and `server.py` in a temporary folder, pins dependencies to exactly what `uv.lock` records, and imports the toolkit with the connection attached. Rerunning it replaces the toolkit; an agent that used the old one needs its tools re-added in the Orchestrate UI.

## If tools answer that the data API could not be reached

The server is running but has no address: the connection is missing or not attached. Rerun the script. A refusal (status 401) instead means a wrong Cloudflare token or API key. A status 403 or a request failure means Cloudflare is not admitting Orchestrate's network; tell Troy.

## Trade-offs against the hosted HTTP server

Each call starts a new process, which adds one to two seconds. Rate limits and the shared HTTP client reset per call, which does not matter at hackathon volume. There are no traces on IBM; the data API on Troy's Mac records every request it receives.
