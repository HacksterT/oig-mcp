# oig-mcp

An MCP server that answers questions across VA Office of Inspector General (OIG) reports: which findings recur across facilities, whether a theme is growing, what peer facilities did in response, and how long similar recommendations take to close. Every answer cites a report number and a vaoig.gov link.

An entry in the [GSA MCP Server and AI Agent Government Hackathon](https://www.gsa.gov/si-community-of-practice/events-and-training/mcp-server-and-si-agent-government-hackathon), Dataset Access track.

- **Proposal:** [troymd.com/mcp-hackathon](https://www.troymd.com/mcp-hackathon)
- **Project overview and deployment plan:** [docs/project-overview.md](docs/project-overview.md)
- **Data:** a structured, regularly refreshed copy of what VA OIG publishes at vaoig.gov, built and served by the companion `oig-data-source` repository. No internal VA systems or nonpublic information are used.

## Status

Early setup. The server runs, connects to clients, and enforces its outbound security boundary. One tool and one resource are live; the goal-level tools are built as the data API comes online.

| Capability | Kind | Status |
|---|---|---|
| `vaoig_get_dataset_status`: data coverage, freshness, reconciliation with the OIG dashboard | Tool | Implemented |
| `vaoig://about`: scope of the data and citation rules | Resource | Implemented |
| Inspection readiness brief | Tool | Planned |
| Search findings | Tool | Planned |
| Theme trend | Tool | Planned |
| Systemic clusters | Tool | Planned |
| Closure performance | Tool | Planned |
| Facility profile | Tool | Planned |
| Report detail | Tool | Planned |
| Topic taxonomy, offices, facilities | Resources | Planned |
| Inspection readiness checklist, aging brief | Prompts | Planned |
| Phoenix evaluation harness with gold questions | Eval | Planned |

## How it fits together

```
vaoig.gov ──> oig-data-source (crawler, SQLite, JSON API in a container behind Cloudflare Access)
                                   │
                                   ▼  OIG_DATA_API_BASE_URL + service token
                     oig-mcp (this repo: tools, resources, prompts, eval)
                                   │
                                   ▼  stdio or streamable HTTP
                     MCP client (Claude Desktop, Claude Code, watsonx Orchestrate, ...)
```

The server calls exactly one origin, configured by the operator, never by a tool argument. The API it expects is documented in [docs/data-api.md](docs/data-api.md).

## Quick start

Requires [uv](https://docs.astral.sh/uv/).

```bash
cp .env.example .env
uv sync
uv run oig-mcp            # stdio; or: uv run python main.py
```

Connect Claude Code or Claude Desktop with:

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

Without the data API running, `vaoig://about` still works and `vaoig_get_dataset_status` returns an error with a hint. See [QUICKSTART.md](QUICKSTART.md) for more.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `OIG_DATA_API_BASE_URL` | `http://127.0.0.1:8787/v1/` | The data API. Must be https unless local. |
| `CF_ACCESS_CLIENT_ID`, `CF_ACCESS_CLIENT_SECRET` | empty | Cloudflare Access service token for the hosted API |
| `STALE_AFTER_DAYS` | `30` | Age at which responses flag data as stale |
| `MCP_TRANSPORT`, `MCP_HOST`, `MCP_PORT` | `stdio`, `0.0.0.0`, `8000` | Transport; a platform-injected `PORT` switches to HTTP automatically |

## Development

Planned and completed work is tracked as features and stories in [`tasks/`](tasks/).

```bash
uv sync --group dev
uv run pytest tests/ -v
uv run ruff check . && uv run ruff format --check .
```

Each tool lives in its own file under `src/oig_mcp/tools/` with a `register(mcp)` function, wired up in `tools/__init__.py`. Resources and prompts follow the same pattern. Tool names use the `vaoig_` prefix, take Pydantic-typed inputs, return structured data with a `provenance` block, and support `response_format` of `json` or `markdown`.

## Deployment

The target is IBM watsonx Orchestrate on IBM Cloud, deployed from an IBM-provided VM with IBM Bob. See [deploy/README.md](deploy/README.md) and [tasks/backlog/F05-ibm-cloud-deployment.md](tasks/backlog/F05-ibm-cloud-deployment.md). The `Dockerfile` serves streamable HTTP on port 8080 with `/mcp`, `/health`, and `/version`. Hosting follows once the data API is reachable from IBM Cloud.

## Security

The outbound boundary is tested: one operator-configured origin, relative paths only, no redirects, no proxy environment, a response size cap, and sanitized upstream errors. The Access token is added by the client and cannot be overridden by a caller. See [SECURITY.md](SECURITY.md).

## Acknowledgements

The project structure and outbound HTTP security boundary are adapted from the [GSA TTS MCP hackathon template](https://github.com/GSA-TTS/mcp-hackathon-template) (MIT). This repository is an independent project and is not maintained with that template.

## License

[MIT](LICENSE). Template code copyright Technology Transformation Services; additions copyright Troy Sybert.
