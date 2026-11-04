# Deployment

The deployment target is IBM watsonx Orchestrate on IBM Cloud. The plan and open questions are in [`docs/project-overview.md`](../docs/project-overview.md).

The server code is the same everywhere. `app.py` picks its transport:

- `PORT` set by the platform (IBM Code Engine sets it): HTTP on that port, with `/mcp`, `/health`, and `/version`
- `MCP_TRANSPORT=streamable-http`: HTTP on `MCP_HOST:MCP_PORT`
- otherwise: stdio

Over HTTP the server requires `MCP_AUTH_TOKEN`, a bearer token that callers present to `/mcp`, and refuses to start without it. Supply it as a secret.

Wherever it runs, the server needs to reach the OIG data API at `OIG_DATA_API_BASE_URL`, with the Cloudflare Access service token supplied as secrets (`CF_ACCESS_CLIENT_ID`, `CF_ACCESS_CLIENT_SECRET`). Never commit them.

## Deployment kit

No kit is checked in yet. F05 chooses one (Code Engine with a hosted `/mcp` URL, or Orchestrate's local stdio toolkit) and adds it here, adapted to this server's configuration and credentials. In the IBM VM, IBM Bob's own deployment skill builds the image from the root `Dockerfile`, pushes it to the shared Container Registry, and deploys on Code Engine. The project-specific plan, configuration, and checks are in [`docs/project-overview.md`](../docs/project-overview.md).
