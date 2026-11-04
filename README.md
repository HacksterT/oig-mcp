# oig-mcp

An MCP server that answers questions across VA Office of Inspector General (OIG) reports: which findings recur across facilities, whether a theme is growing, what peer facilities did in response, and how long similar recommendations take to close. Every answer cites a report number and a vaoig.gov link.

An entry in the [GSA MCP Server and AI Agent Government Hackathon](https://www.gsa.gov/si-community-of-practice/events-and-training/mcp-server-and-si-agent-government-hackathon), Dataset Access track.

- **Proposal:** [troymd.com/mcp-hackathon](https://www.troymd.com/mcp-hackathon)
- **Project overview and deployment plan:** [docs/project-overview.md](docs/project-overview.md)
- **Data:** a structured, regularly refreshed copy of what VA OIG publishes at vaoig.gov, built and served by the companion `oig-data-source` repository. No internal VA systems or nonpublic information are used.

## Status

The server is built, and it answers from the full data build of November 4, 2026, covering 4,415 reports and 15,649 recommendations. It has been evaluated on Claude models, and deployment to IBM watsonx Orchestrate is next. Results are in [docs/evaluation.md](docs/evaluation.md).

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
| `OIG_DATA_API_BASE_URL` | `http://127.0.0.1:8787/v1/` | The data API. Must be https unless local |
| `CF_ACCESS_CLIENT_ID`, `CF_ACCESS_CLIENT_SECRET` | empty | Cloudflare Access service token for the hosted API |
| `MCP_AUTH_TOKEN` | empty | Bearer token for `/mcp`. Required over HTTP, unused over stdio |
| `STALE_AFTER_DAYS` | `30` | Age at which responses flag data as stale |
| `MCP_TRANSPORT`, `MCP_HOST`, `MCP_PORT` | `stdio`, `0.0.0.0`, `8000` | Transport; a platform-injected `PORT` switches to HTTP automatically |

## Development

```bash
uv sync --group dev
uv run pytest tests/ -v
uv run ruff check . && uv run ruff format --check .
```

Each tool lives in its own file under `src/oig_mcp/tools/` with a `register(mcp)` function, wired up in `tools/__init__.py`. Resources and prompts follow the same pattern. Tool names use the `vaoig_` prefix, take Pydantic-typed inputs, and return structured data with a `provenance` block that says how to cite the result.

## Deployment

The target is IBM watsonx Orchestrate on IBM Cloud, deployed from an IBM-provided VM with IBM Bob. See [deploy/README.md](deploy/README.md) and [docs/project-overview.md](docs/project-overview.md). The `Dockerfile` serves stateless streamable HTTP on port 8080 with `/mcp`, `/health`, and `/version`.

## Evaluation

An assistant answers 23 questions using only these tools, scored against answers computed by SQL from a pinned snapshot, with traces in Arize Phoenix. See [docs/evaluation.md](docs/evaluation.md) for results and [eval/README.md](eval/README.md) to run it.

## Security

Callers authenticate to `/mcp` with a bearer token, and the server authenticates to the data API with a separate Cloudflare Access token. The outbound boundary is tested: one operator-configured origin, relative paths only, no redirects, no proxy environment, a response size cap, and sanitized upstream errors. See [SECURITY.md](SECURITY.md).

## Acknowledgements

The project structure and outbound HTTP security boundary are adapted from the [GSA TTS MCP hackathon template](https://github.com/GSA-TTS/mcp-hackathon-template) (MIT). This repository is an independent project and is not maintained with that template.

## License

[MIT](LICENSE). Template code copyright Technology Transformation Services; additions copyright Troy Sybert.
