# oig-mcp

An MCP server that answers questions across VA Office of Inspector General (OIG) reports: which findings recur across facilities, whether a theme is growing, what peer facilities did in response, and how long similar recommendations take to close. Every answer cites a report number and a vaoig.gov link.

An entry in the [GSA MCP Server and AI Agent Government Hackathon](https://www.gsa.gov/super-intelligence/si-community-of-practice/events-and-training/mcp-server-and-si-agent-government-hackathon), Dataset Access track.

- **Documentation:** [the wiki](docs/README.md) is the full account: mission, architecture, guides, and evaluation. This README is the short overview.
- **Proposal:** [troymd.com/mcp-hackathon](https://www.troymd.com/mcp-hackathon)
- **Data:** a structured, regularly refreshed copy of what VA OIG publishes at vaoig.gov, built and served by the companion `oig-data-source` repository, which is private. [Data API](docs/architecture/data-api.md) documents the API this server expects from it. No internal VA systems or nonpublic information are used.

## Status

The server is complete. Its scores were measured at tag `eval-final-2`; the one later server change ([#114](https://github.com/HacksterT/oig-mcp/pull/114)) only tells the AI when the user picked a facility and reads a state in a facility name. It answers from the full data build of November 4, 2026, covering 4,410 reports and 15,649 recommendations, is deployed in IBM watsonx Orchestrate as a local toolkit, and is hosted for testers at `https://mcp.troymd.com/mcp`. It was tested with five models from four model makers: Claude Opus 5.5 and Sonnet 5.5, GPT-OSS 120B in IBM watsonx Orchestrate, Llama 3.3 70B on watsonx.ai, and DeepSeek V4 Pro. On 24 questions scored against SQL-computed answers, models pass 2 or 3 without the server; with it, Claude Opus 23, Claude Sonnet 22, GPT-OSS 12, and Llama 9. That spread is a finding in itself: [what five models taught us](docs/evaluation/results.md#same-server-five-models). With only the server changed, GPT-OSS rose from 10, 8, and 11 to 12 and 12. Every saved score can be recomputed with one command and no keys: [Verify it yourself](docs/evaluation/method.md#verify-it-yourself).

| Capability | Kind |
|---|---|
| `vaoig_get_dataset_status`: data coverage, freshness, reconciliation with OIG, filter values | Tool |
| `vaoig_search_findings`: the one search tool, keyword and semantic on every query | Tool |
| `vaoig_get_report`: one report with every recommendation and facility response | Tool |
| `vaoig_get_facility_profile`: one facility's reports, inspections, findings, and repeat findings | Tool |
| `vaoig_analyze_recommendations`: counts, trends, time to close, and aging by year, office, topic, or report type | Tool |
| `vaoig_find_systemic_clusters`: findings that recur across reports, and how common they are | Tool |
| `vaoig_get_inspection_brief`: one facility's history, common peer findings, peer commitments, and estimated next window | Tool |
| `vaoig://about`, `vaoig://facilities`, `vaoig://taxonomy/{facet}` | Resources |
| Inspection readiness checklist, open-recommendation aging brief | Prompts |
| When a facility name matches several, the user is asked to choose, in hosts that support elicitation; other hosts get the matches and an instruction to ask | Elicitation |
| Suggested values as a person types: facilities (name and station) for the checklist, OIG topics for the aging brief, facet names for the taxonomy | Completions |

## How it fits together

```
vaoig.gov ──> oig-data-source (crawler, SQLite, JSON API in a container behind Cloudflare Access)
                                   │
                                   ▼  OIG_DATA_API_BASE_URL + service token
                     oig-mcp (this repo: tools, resources, prompts, eval)
                                   │
                                   ▼  stdio or Streamable HTTP
                     MCP client (Claude Desktop, Claude Code, watsonx Orchestrate, ...)
```

The server calls exactly one origin, configured by the operator, never by a tool argument. The API it expects is documented in [Data API](docs/architecture/data-api.md), and how the private pipeline builds and checks the data, from crawl to facility responses to reconciliation with OIG, is in [Data source](docs/architecture/data-source.md).

## Quick start

Requires [uv](https://docs.astral.sh/uv/).

```bash
cp .env.example .env      # then set OIG_DATA_API_BASE_URL; for the hosted API, also the Cloudflare and API key values
uv sync
uv run oig-mcp            # stdio: waits silently for an MCP client; Ctrl-C to stop
```

Connect Claude Code (`.mcp.json`) or Claude Desktop (`claude_desktop_config.json`):

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

Then ask: "Read vaoig://about, then check the OIG dataset status." Without the data API running, the resource still works and the status tool returns an error with a hint.

To serve over HTTP on this machine:

```bash
export MCP_AUTH_TOKEN=$(openssl rand -hex 32)
MCP_TRANSPORT=streamable-http uv run oig-mcp
curl http://localhost:8000/health
```

The MCP endpoint is `http://localhost:8000/mcp`, and callers send `Authorization: Bearer <MCP_AUTH_TOKEN>`. The server will not start over HTTP without a token, listens on `127.0.0.1` only, and refuses requests whose Host or Origin header names another site. To run the container image instead, use `docker compose up -d --build`. To connect to the hosted copy as a tester, see [Connecting](docs/guides/connecting.md).

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `OIG_DATA_API_BASE_URL` | `http://127.0.0.1:8787/v1/` | The data API. Must be https unless local |
| `CF_ACCESS_CLIENT_ID`, `CF_ACCESS_CLIENT_SECRET` | empty | Cloudflare Access service token for the hosted API |
| `OIG_DATA_API_KEY` | empty | The data API's own key, sent as `Authorization: Bearer` behind Access. Must match the API's `OIG_API_KEY` |
| `MCP_AUTH_TOKEN` | empty | Bearer token for `/mcp`. Required over HTTP, unused over stdio |
| `MCP_CLIENT_TOKENS` | empty | More bearer tokens, as `name:token,name:token`, so one client can be removed alone. Managed with `deploy/mcp_clients.py` |
| `MCP_USAGE_LOG` | empty | File for the usage log, which also goes to stderr. Records client, tool, outcome, and duration, never arguments |
| `MCP_TRACE_DIR`, `MCP_TRACE_MAX_MB` | empty, `400` | Full traces of tool calls and resource reads, including arguments and results. On through the hackathon, including judging, and disclosed to users in `vaoig://about`. Read them with `deploy/traces.py` |
| `STALE_AFTER_DAYS` | `30` | Age at which responses flag data as stale |
| `MCP_TRANSPORT`, `MCP_HOST`, `MCP_PORT` | `stdio`, `127.0.0.1`, `8000` | `stdio`, or `streamable-http` for Streamable HTTP, the MCP specification's HTTP transport (FastMCP calls it `http`); anything else stops startup. Host and port apply to local HTTP, which checks Host and Origin headers. A platform-injected `PORT` switches to HTTP on all interfaces |

## Development

```bash
uv sync --group dev
uv run pytest tests/ -v
uv run ruff check . && uv run ruff format --check .
```

Each tool lives in its own file under `src/oig_mcp/tools/` with a `register(mcp)` function; tool names use the `vaoig_` prefix, inputs are Pydantic-typed and bounded, and every tool declares an output schema. FastMCP sends a tool's docstring only up to its `Returns:` section, so anything a model needs to choose or chain tools goes above it. The code map, request flow, and design rules are in [Server design](docs/architecture/server-design.md).

## Deployment

The same server runs over both MCP transports; only how a host starts it differs.

| Transport | Used by | How |
|---|---|---|
| stdio | watsonx Orchestrate, desktop hosts (Claude Desktop, VS Code, Cursor, Grok) | The host starts the server as a local process, with no network endpoint. In Orchestrate it runs as a local toolkit ([deploy/ibm/local-mcp-toolkit/](deploy/ibm/local-mcp-toolkit/README.md)) |
| Streamable HTTP | Remote agents, testers, and the evaluation harness, at `https://mcp.troymd.com/mcp` with a bearer token per client | The `Dockerfile` serves `/mcp`, `/health`, and `/version` on port 8080, with a session per client so the server can ask the user mid-call on any protocol version |

Setup for each host: [Connecting](docs/guides/connecting.md). Deployments, checks, and operations: [Deployment and operations](docs/guides/deployment.md).

## Evaluation

An agent answers 24 questions, plus 6 adversarial ones, using only these tools, scored against answers computed by SQL from a pinned snapshot, on five models: Claude Opus 5.5 and Sonnet 5.5, GPT-OSS 120B in watsonx Orchestrate, Llama 3.3 70B on watsonx.ai, and DeepSeek V4 Pro through Hermes Agent. How the testing works: [Method](docs/evaluation/method.md). What it found: [Results](docs/evaluation/results.md). Whether the changes helped: [Debrief](docs/evaluation/debrief.md). To run it: [eval/README.md](eval/README.md).

## Security

Over HTTP, callers authenticate to `/mcp` with a bearer token, with a rate limit per token. In watsonx Orchestrate the server runs over stdio inside Orchestrate's runtime, with no network endpoint. The server authenticates to the data API with a separate Cloudflare Access token and the API's own key. The outbound boundary is tested: one operator-configured origin, relative paths only, no redirects, no proxy environment, a response size cap, and sanitized upstream errors. Every tool is read-only, and report text is marked as quoted source material, not instructions. Questions and answers are recorded during the hackathon, and users are told. See [SECURITY.md](SECURITY.md).

## Acknowledgements

The project structure and outbound HTTP security boundary are adapted from the [GSA TTS MCP hackathon template](https://github.com/GSA-TTS/mcp-hackathon-template) (MIT). This repository is an independent project and is not maintained with that template. The agent skills in `.agents/skills/` came with that template; `mcp-builder` originates in [Anthropic's skills repository](https://github.com/anthropics/skills/tree/main/skills/mcp-builder) and is under the Apache License 2.0, included as `.agents/skills/mcp-builder/LICENSE.txt`.

## License

[MIT](LICENSE). Template code copyright Technology Transformation Services; additions copyright Troy Sybert.
