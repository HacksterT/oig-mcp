[Wiki](../README.md) › Architecture › Server design

# Server design

*How the MCP server is built: what it exposes, how a request flows through it, and the design rules every tool follows.*

## What it exposes

| Name | Kind | What it returns |
|---|---|---|
| `vaoig_get_dataset_status` | Tool | Data date, counts, reconciliation with OIG, and the valid filter values |
| `vaoig_search_findings` | Tool | Ranked recommendations and corrective actions for a question in any wording |
| `vaoig_get_report` | Tool | One report with every recommendation and facility response |
| `vaoig_get_facility_profile` | Tool | One facility's reports, inspections, findings, and repeat findings |
| `vaoig_analyze_recommendations` | Tool | Counts, trends, time to close, and aging by year, office, topic, or report type |
| `vaoig_find_systemic_clusters` | Tool | Findings that recur across reports, and how common they are |
| `vaoig_get_inspection_brief` | Tool | One facility's history, common peer findings, peer commitments, and an estimated next window |
| `vaoig://about`, `vaoig://facilities`, `vaoig://taxonomy/{facet}` | Resources | Scope and citation rules, the facility registry, and OIG's filter values |
| `inspection_readiness_checklist`, `open_recommendation_aging_brief` | Prompts | Reusable workflows |

When to use each tool, with its inputs: [Tools](../guides/tools.md).

## How a request flows

```
MCP host ──> transport (stdio, or Streamable HTTP with a bearer token)
         ──> TraceMiddleware        one trace per call, linked to the data API by trace ID
         ──> UsageLogMiddleware     one line per call: client, tool, outcome, time
         ──> ClientRateLimitMiddleware   2 calls a second per token, bursts to 30; listings not counted
         ──> ToolFailureMiddleware  a failure becomes an MCP error result with a hint
         ──> the tool ──> upstream.py ──> the data API (at most 8 requests in flight)
```

## Code map

| Path | Contents |
|---|---|
| `src/oig_mcp/app.py` | Creates the server, registers everything, chooses the transport |
| `src/oig_mcp/tools/` | One file per tool, each with `register(mcp)` |
| `src/oig_mcp/resources/`, `src/oig_mcp/prompts/` | The three resources and two prompts |
| `src/oig_mcp/models.py` | Pydantic models: input filters and enums, `Provenance`, and each tool's output schema |
| `src/oig_mcp/upstream.py` | The one hardened HTTP client: relative paths only, no redirects, a size cap, the concurrency limit |
| `src/oig_mcp/failures.py` | Upstream errors and the hint chosen for each cause |
| `src/oig_mcp/guidance.py` | Texts that travel in results: citation guidance, notices, next steps |
| `src/oig_mcp/results.py` | Result shaping: provenance, paging, citations, shortened responses |
| `src/oig_mcp/middleware.py`, `tracing.py`, `auth.py` | The middleware above, trace storage, and the bearer token check |
| `src/oig_mcp/facility_choice.py`, `completions.py`, `http_sessions.py` | Elicitation, argument completions, and optional HTTP sessions ([MCP features](mcp-features.md)) |
| `tests/` | 275 tests: every tool's inputs, results, and schema; errors and hints; authentication; security boundaries |

## Design rules

**Tools built around a user's goal, not the API's endpoints.** Seven tools, each named for a task, several of which combine many data requests: the inspection brief alone runs up to ten searches, so a model makes one call instead of sequencing ten. Counts come only from the analysis tool, never from adding up search results, and every description says when to use another tool instead.

**Typed, bounded contracts in both directions.** Enums cover closed sets; filters reject unknown fields rather than dropping them, because a dropped filter would silently answer for a wider set; every list, string, and offset is bounded. Every tool declares an output schema, so a host sees a result's shape before calling. Common mistakes are corrected at the boundary: an office name in the wrong filter is refused with the fix, and an empty result says to check the filter values before concluding there is nothing.

**Trust carried in every answer, by the server.** Guardrails live in the server's instructions and results, not in one host's prompt, so they hold for every agent that connects. Every result has provenance (the data date, whether it is stale, how to cite it) and notices the assistant must pass on. Report text is marked as quoted source material, never instructions, and every tool is read-only. Scope is stated by the server: no medical, benefits, or legal advice; emergencies sent to 911; no ratings, rankings, or forecasts; never a guess about who was responsible.

**Failures an agent can act on.** A failure returns a short MCP error with a hint chosen by cause: a rejected filter, a busy search queue, a slow search, a data service failure, or an unreachable service. It never carries a stack trace, address, or credential. "Not found" and "several facilities match" are answers, not errors.

**One outbound origin.** Every call goes through `upstream.py` to the operator-configured data API, with relative paths only. No tool can name a URL.

Measured against the ten anti-patterns in IBM's MCP design guide, the server fully meets four, mostly meets two, and partly meets four; the table with evidence for each is in the [evaluation document](../submission/evaluation-document.md#measured-against-ibms-mcp-design-guide). Security in depth: [SECURITY.md](../../SECURITY.md).

---

← [Data API](../architecture/data-api.md) · [Wiki home](../README.md) · [MCP features](../architecture/mcp-features.md) →
