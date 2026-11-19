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
| `tests/` | 313 tests: every tool's inputs, results, and schema; errors and hints; authentication; security boundaries |

## Design rules

**Tools built around a user's goal, not the API's endpoints.** Seven tools, each named for a task, several of which combine many data requests: the inspection brief alone runs up to ten searches, so a model makes one call instead of sequencing ten. Counts come only from the analysis tool, never from adding up search results, and every description says when to use another tool instead.

**Typed, bounded contracts in both directions.** Enums cover closed sets; filters reject unknown fields rather than dropping them, because a dropped filter would silently answer for a wider set; every list, string, and offset is bounded. Every tool declares an output schema, so a host sees a result's shape before calling. Common mistakes are corrected at the boundary: an office name in the wrong filter is refused with the fix, and an empty result says to check the filter values before concluding there is nothing.

**Trust carried in every answer, by the server.** Guardrails live in the server's instructions and results, not in one host's prompt, so they hold for every agent that connects. Every result has provenance (the data date, whether it is stale, how to cite it) and notices the assistant must pass on. Report text is marked as quoted source material, never instructions, and every tool is read-only. Scope is stated by the server: no medical, benefits, or legal advice; emergencies sent to 911; no ratings, rankings, or forecasts; never a guess about who was responsible.

**Failures an agent can act on.** A failure returns a short MCP error with a hint chosen by cause: a rejected filter, a busy search queue, a slow search, a data service failure, or an unreachable service. It never carries a stack trace, address, or credential. "Not found" and "several facilities match" are answers, not errors.

**One outbound origin.** Every call goes through `upstream.py` to the operator-configured data API, with relative paths only. No tool can name a URL.

Measured against the ten anti-patterns in IBM's MCP design guide, the server fully meets four, mostly meets two, and partly meets four: see [below](#measured-against-ibms-mcp-design-guide). Security in depth: [SECURITY.md](../../SECURITY.md).

## Measured against IBM's MCP design guide

IBM's guide for MCP tools in watsonx Orchestrate, "[MCP tools & integration considerations](https://developer.watson-orchestrate.ibm.com/agents/agent_design/mcp_integration.md)" (read November 17, 2026), lists ten anti-patterns, three marked as the most common (★), with a fix for each. This table holds the server to that standard. "Partial" means the fix is in place but not complete; the last column says what is missing. In all: four fully met, two mostly met, four partly met.

| Anti-pattern | IBM's fix | This server | Evidence |
|---|---|---|---|
| ★ The glorified API wrapper | Business capability tools | Mostly avoided. The tools answer goals, such as an inspection brief, a facility profile, and recurring findings, and compose the data API's generic endpoints behind them. `vaoig_get_report` and `vaoig_search_findings` sit closer to single endpoints. | The brief makes up to 14 data API calls per call ([`inspection_brief.py`](../../src/oig_mcp/tools/inspection_brief.py)); [Data API](data-api.md) treats an endpoint that mirrors one tool as a design smell |
| Raw schema leakage | Business-level abstractions | Partial. Results add business fields (citations, a peak year, estimates labeled as estimates, quoted fields, notices), but records otherwise pass through with the data API's field names, such as `rec_id` and `node_id`. | `with_citations`, `peak_year`, and the `*_basis` fields; the profile drops internal fields (#84) |
| Wishful delegation | Encode complexity in tools | Mostly. Done for the steps that failed in testing: facility resolution with retries, office names turned into abbreviations, the peak year named, peer actions gathered for the brief, and a choice of facility put to the user. Some reasoning is still left to the model, such as filtering a facility's reports by type. | `test_office_filter_sends_a_known_office_as_its_abbreviation`, `test_year_analysis_names_the_peak_year`, [`facility_choice.py`](../../src/oig_mcp/facility_choice.py); GPT-OSS 120B passed 8 to 11 of 24 in the first Orchestrate round, before the latest changes |
| Anything-in, garbage-out | Strong contracts | Done. Every argument is typed and bounded, unknown filter names are refused (`extra="forbid"`), facets come from a fixed list, and an empty result says to check the filter values. | `test_unknown_filter_is_rejected_not_ignored`, `test_unknown_facet_is_refused_without_a_request`; 49 robustness checks |
| The god-mode tool | Constrained capabilities | Done. Seven read-only tools, no URL arguments, one fixed upstream origin, and a per-client rate limit. | `readOnlyHint` on every tool; `test_fetch_json_uses_fixed_origin_and_safe_client_policy` |
| ★ The data firehose | Bounded outputs | Partial, and the main exposure found in testing. Every list is paged and capped, search returns a shortlist, and long narratives are shortened. Llama 3.3 70B still overflowed its context on one question, by calling the facility profile eight times. A 100-item profile page went from 70,126 to 40,906 characters; Llama has not been rerun since. | [Result size](../evaluation/results.md#result-size); [`eval/payload_sizes.py`](../../eval/payload_sizes.py) |
| The trusted output trap | Sanitize outputs | Partial, by design. Report text is quoted verbatim, because it is the evidence, so it is marked rather than rewritten: every result names its quoted fields and says never to follow instructions in them. Server notices use only integers from upstream. | `test_tools_that_return_report_text_say_it_is_quoted`; the injected-text adversarial question passed for Claude Opus 5.5 throughout, and for Llama 3.3 70B after the server changes |
| ★ The "kitchen sink" server | Contextual discovery | Avoided. Seven tools; the server's instructions map each user goal to one tool; descriptions say when to use a different tool; filter values come from `vaoig_get_dataset_status`. | `test_routing_hints_reach_the_client`; tool choice 20 of 20 (Claude) and 19 of 20 (Llama) |
| The useless error | Structured errors | Partial. Failures are MCP error results with `{error, hint}`: no stack trace or internal detail, and a hint chosen by the cause. They carry no machine-readable `error_code` or `field`, as IBM's format suggests. | `test_upstream_failures_get_a_hint_for_their_cause`; robustness checks inspect every reply for internal detail |
| The stateful tool trap | Stateless tools | Done. No tool keeps state between calls: every answer depends only on its arguments and the data. The hosted endpoint keeps a session per client only to carry a question to the user mid-call, and idle sessions close after 30 minutes; the rate limit's counters also live in memory. | `test_platform_port_serves_http_sessions_with_token`; the robustness check asks a client on each protocol version over HTTP |

**The agent-ready checklist.** IBM's seven questions, answered for each tool. Reasoning is what the model must still do with the result.

| Tool | Business action? | Constrained inputs? | Non-expert friendly? | Safe by default? | Logic location | Reasoning required | Designed for agents? |
|---|---|---|---|---|---|---|---|
| `vaoig_get_dataset_status` | Yes: how current is the data | No inputs | Yes | Read-only | Server: reconciliation notices | Low | Yes: lists the valid filter values |
| `vaoig_search_findings` | Yes: find what OIG cited | Typed, bounded filters | Plain-language question | Read-only | Server: hybrid search, shortlist notice | Medium: pick what is relevant | Yes: citation per record |
| `vaoig_get_report` | Partly: look up one report | One of two typed identifiers | Needs a report number | Read-only | Server: number to record | Low | Yes: not-found says not to substitute |
| `vaoig_get_facility_profile` | Yes: a facility's history | Name, city, or station; bounded paging | Yes: plain names work | Read-only | Server: resolution, choice, repeats | Medium: filter reports by type | Yes |
| `vaoig_analyze_recommendations` | Yes: counts and time to close | Enumerated groupings, typed filters | Mostly: office names accepted | Read-only | Server: peak year, notices on target dates | Medium: read a table | Yes |
| `vaoig_find_systemic_clusters` | Yes: what recurs | Typed, bounded | Mostly | Read-only | Server: prevalence wording, caveats | Medium | Yes |
| `vaoig_get_inspection_brief` | Yes: prepare for an inspection | Name, city, or station | Yes | Read-only | Server: up to 14 calls composed | Low | Yes: one call for the whole task |

IBM's guide also describes two patterns: tools that are business capabilities, exposed to the agent directly, or an "agent-ready facade" built over generic tools. This server is the first pattern, over a data API that plays the generic layer.

---

← [Data API](../architecture/data-api.md) · [Wiki home](../README.md) · [MCP features](../architecture/mcp-features.md) →
