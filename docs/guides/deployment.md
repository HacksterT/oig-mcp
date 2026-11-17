[Wiki](../README.md) › Guides › Deployment and operations

# Deployment and operations

*Where the server is deployed, how each deployment is checked, and how it is run day to day. Step-by-step commands are in [`deploy/README.md`](../../deploy/README.md), next to the scripts they run.*

## Deployments

| Where | Transport | How it is set up |
|---|---|---|
| IBM watsonx Orchestrate | stdio, inside Orchestrate's runtime | A local toolkit registered from an IBM-provided VM, with the data API's settings in a key_value connection: [`deploy/ibm/local-mcp-toolkit/`](../../deploy/ibm/local-mcp-toolkit/README.md) |
| Hosted endpoint, `https://mcp.troymd.com/mcp` | Streamable HTTP | The root `Dockerfile` image, run with `docker compose` and reached through a Cloudflare Tunnel, with a named bearer token per tester |
| Any desktop host | stdio | `uv run oig-mcp` from a clone: [Connecting](connecting.md) |

The image installs dependencies from `uv.lock`, runs as a non-root user with every Linux capability dropped, a read-only filesystem, and memory and process limits, and serves `/mcp`, `/health`, and `/version` on port 8080. IBM Code Engine was planned and not used, because the hackathon account had none set up; the image would run there unchanged.

## Checks

Each runs against a build or a live server, with no model involved.

| Check | What it proves | Latest result |
|---|---|---|
| `deploy/verify_image.sh` | The image holds no secrets, refuses to start unsafely, and works with good credentials | 15 of 15 |
| `deploy/verify_deployment.py` | Who may reach `/mcp` (8 ways of being refused), that it opens a session, and that tools get live data | 22 of 22 |
| `deploy/robustness_check.py` | Every tool under traversal, injection, out-of-bound values, and bursts past every limit; each reply checked for stack traces, addresses, and credentials; the facility question on both protocol versions | 49 of 49 |
| `deploy/load_test.py` | Throughput and latency from 1 to 40 concurrent clients | 2,059 of 2,059 calls answered ([results](../evaluation/results.md#load-test)) |
| `tests/`, on every change in CI | Every tool's inputs, results, schemas, errors, authentication, and security boundaries | 300 pass |

## Operations

**Configuration.** All settings come from the environment or `.env`; the server refuses to start over HTTP without a token, and refuses a data API address that is not https. Reference: [Configuration](../../README.md#configuration).

**Testers.** `deploy/mcp_clients.py` adds, lists, and removes named tokens; each change restarts the container for a few seconds.

**Limits.** Two MCP requests a second per token, with bursts to 30; listings are not counted. At most eight requests to the data API in flight per process, so a burst of tool calls cannot overwhelm it. HTTP sessions close after 30 minutes idle.

**Logs and traces.** A usage log records one line per tool call or resource read: client, tool, outcome, time, and trace ID. Each call's trace holds its arguments, every data API request it made, and its result, and the trace ID links it to the data API's own trace of the same request. Traces stay on through judging and are capped in size; `deploy/traces.py` reads them.

**After a code change.** Rebuild with `docker compose up -d --build`, then run the deployment check, and the robustness check when no one else is using the data API, because it deliberately floods it.

**Security.** The full design, every check, and the independent review: [SECURITY.md](../../SECURITY.md).

---

← [Tools](../guides/tools.md) · [Wiki home](../README.md) · [Decisions](../guides/decisions.md) →
