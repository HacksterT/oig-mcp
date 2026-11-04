# Project Overview and Deployment Plan

**Audience:** IBM Bob, working in the IBM-provided VM on a clone of this repository, and Troy Sybert, the project owner.
**Status as of:** 2026-11-04.
**Purpose:** Explain what this project is, how its parts fit together, what already exists, and what Bob should and should not do on the IBM side.

Bob: start with [the deployment handoff](handoff/2026-11-04-troy-bob-deployment-handoff.md), which has the steps, what is tested, and every assumption about IBM. This document holds the background and the rules.

Read this whole document before taking any action. Bob's own skills handle general mechanics such as deployment. Where a skill and this document disagree about something specific to this project (ports, health check path, configuration, naming, rules), this document wins. Where a step needs a value this document does not give (initials, account names, URLs, keys), ask Troy. Do not guess.

---

## 1. The project in brief

`oig-mcp` is a Model Context Protocol (MCP) server that lets an AI assistant answer questions across VA Office of Inspector General (OIG) reports and recommendations. Examples:

- Which findings recur across VA medical facilities?
- Is a theme such as suicide prevention growing year over year?
- What did peer facilities commit to doing when cited for the same problem?
- How long do similar recommendations take to close, by office and topic?
- What has OIG found at one facility before its next inspection?

Every answer must cite a report number and a vaoig.gov link, and must state the date the data was collected.

All data comes from what VA OIG publishes publicly at vaoig.gov. The project uses no internal VA systems, no internal VA data, and no nonpublic information.

The primary users are facility patient safety and quality staff preparing for OIG inspections. The public proposal is at https://www.troymd.com/mcp-hackathon.

## 2. The hackathon

This is an entry in the GSA MCP Server and AI Agent Government Hackathon, **Dataset Access track**: enable AI applications to query open government datasets.

| Item | Detail |
|---|---|
| Sponsors and partners | GSA, with IBM, Databricks, OpenAI, and Prefect supporting |
| This project's platform | IBM: watsonx Orchestrate on IBM Cloud |
| Judging criteria | Technical quality (including participant-run evaluation and MCP design: Pydantic models, precise tool names, goal-oriented tools), innovation, mission alignment (service delivery and oversight), presentation |
| Deliverables | A GitHub repository with documented server code, a presentation deck, and an evaluation document |
| Key dates | Halfway check-in Nov 3, 2026; closing ceremony Dec 16, 2026; final submission deadline not yet announced |

## 3. Architecture

The project is two repositories.

| Repository | What it does | Where it runs | Visibility |
|---|---|---|---|
| `oig-data-source` | Crawls vaoig.gov, parses report pages and PDFs, builds a SQLite database, serves a JSON API over it | Troy's Mac mini, exposed to the internet through a Cloudflare Tunnel with Cloudflare Access service tokens | Private |
| `oig-mcp` (this repo) | The MCP server: tools, resources, prompts, evaluation | Developed on Troy's Mac; deployed to IBM Cloud Code Engine from the IBM VM; registered in watsonx Orchestrate | Public (planned) |

```
vaoig.gov (public OIG pages and PDFs)
      │  crawled by
      ▼
oig-data-source on Troy's Mac
  SQLite database ──> JSON API ──> Cloudflare Tunnel ──> Cloudflare Access
                                                                         │
                                       HTTPS + service token headers     │
                                                                         ▼
oig-mcp on IBM Code Engine  (container from this repo's Dockerfile)
  /mcp  /health  /version
      │  streamable HTTP, Authorization: Bearer MCP_AUTH_TOKEN
      ▼
watsonx Orchestrate  (remote MCP toolkit + an agent that uses it)
      │
      ▼
User
```

The MCP server calls exactly one outbound origin: the data API set in `OIG_DATA_API_BASE_URL`. It never fetches vaoig.gov or any other site directly, and no tool argument can change where it connects.

## 4. Current state

| Component | State |
|---|---|
| Seven tools, three resources, two prompts | Built and tested |
| Bearer authentication on `/mcp` | Built and tested on both connections. See `deploy/verify_deployment.py` |
| Container image | Built from `uv.lock`, runs as non-root, stateless HTTP with JSON responses |
| Evaluation (Arize Phoenix) | Run on two Claude models. Results are in [`evaluation.md`](evaluation.md) |
| `oig-data-source` crawler, database, and API | Live behind Cloudflare Access, with the full data build of 2026-11-04 |
| IBM Cloud deployment | Not started. This is Bob's area (F05) |

## 5. Repository tour

| Path | Contents |
|---|---|
| `src/oig_mcp/app.py` | Creates the FastMCP server, registers everything, chooses the transport |
| `src/oig_mcp/config.py` | Settings from environment variables; validates the data API URL |
| `src/oig_mcp/utils.py` | The hardened HTTP client (`fetch_json`), Access headers, provenance helper |
| `src/oig_mcp/models.py` | Pydantic models and enums: `RecommendationStatus`, `PaginationParams`, `Provenance` |
| `src/oig_mcp/tools/` | One file per tool; `__init__.py` registers them |
| `src/oig_mcp/auth.py` | The bearer token check for `/mcp` |
| `src/oig_mcp/resources/` | `vaoig://about`, `vaoig://facilities`, `vaoig://taxonomy/{facet}` |
| `src/oig_mcp/prompts/` | Two workflow prompts |
| `src/oig_mcp/routes.py` | `/health` and `/version` HTTP routes |
| `tests/` | Security, authentication, tool, and server tests |
| `eval/` | The evaluation harness and gold questions |
| `docs/evaluation.md` | Evaluation results and method |
| `docs/data-api.md` | The API contract this server expects from `oig-data-source` |
| `docs/project-overview.md` | This document |
| `deploy/` | Deployment settings, and scripts that check an image and a running server |
| `compose.yaml` | Runs the image locally for testing with any MCP client |
| `Dockerfile` | Python 3.11 slim image; serves streamable HTTP on port 8080 |
| `.agents/skills/` | Agent skills carried from the GSA template. The handoff lists where they differ from this server |
| `docs/handoff/` | Handoff reports between Bob and Troy, and `TEMPLATE.md` for writing them |

## 6. Conventions to follow

If Bob changes code, these rules apply. Troy does most development on his Mac, so code changes on the IBM side should be small and deployment-related.

- **One tool per file** in `src/oig_mcp/tools/`, each exposing `register(mcp)` and added to `tools/__init__.py`.
- **Tool names** use the `vaoig_` prefix and a verb: `vaoig_get_...`, `vaoig_find_...`, `vaoig_search_...`.
- **Typed inputs** with Pydantic models or enums; read-only annotations on every tool.
- **Every response** includes a `provenance` block built with `build_provenance()`, and every record carries a report number and a vaoig.gov URL.
- **Errors** return `{"error": ..., "hint": ...}` with a short, safe message. Never return upstream response bodies, URLs, headers, or stack traces.
- **Outbound calls** go only through `fetch_json()` with a relative path. Never add another HTTP client, and never accept a URL from a tool argument.
- **Before any commit:** `uv run ruff check .`, `uv run ruff format --check .`, and `uv run pytest tests/` must pass.
- **Planning** documents are kept outside this repository. Record what was done in a handoff report under `docs/handoff/`.

## 7. Bob's role

Bob's job is **F05: deploy `oig-mcp` to IBM Cloud and register it in watsonx Orchestrate.** Bob's own deployment skill handles the mechanics. The [deployment handoff](handoff/2026-11-04-troy-bob-deployment-handoff.md) gives the phases, the assumptions to confirm, and how to tell each phase worked. [`deploy/README.md`](../deploy/README.md) lists the settings.

## 8. Handoff and communication

Troy develops on his Mac. Bob works in the IBM VM. GitHub is the only channel between the two copies of this repository, and written handoff reports are the record of what happened on each side.

### What Troy provides to Bob

| Item | When | How |
|---|---|---|
| Access to this repository | Before the first session | GitHub |
| Initials for resource names | Known | `TES` |
| IBM Cloud account, resource group, and Code Engine project to use | Before Phase 2 | Troy tells Bob directly |
| watsonx Orchestrate instance URL and API key | Before Phase 3 | Entered by Troy in the VM only; never written to the repository |
| Data API URL and Cloudflare Access service token | Before Phase 1 | Entered as platform secrets only; never written to the repository |

When Bob receives a secret, confirm receipt without repeating its value anywhere.

### How Bob reports back

- Write each report as a Markdown file in `docs/handoff/`, named `YYYY-MM-DD-bob-<topic>.md` (for example `2026-11-05-bob-code-engine.md`). Copy the structure from `docs/handoff/TEMPLATE.md`.
- One report per assignment or phase. Keep it factual: what was done, what was observed, exact error text, names and URLs created. No secrets, keys, or tokens.
- Put questions for Troy in the report's "Questions for Troy" section. If a question blocks all progress, also ask Troy directly in the session.
- Troy answers in the report's "Troy's response" section, or in a new file named `YYYY-MM-DD-troy-<topic>.md`.

### How changes move between the Mac and the VM

- At the start of every session, pull the latest `main`.
- Do all work on a branch named `ibm/<short-topic>` (for example `ibm/deploy`). Commit the handoff report on that branch along with any change.
- Push the branch and tell Troy it is ready. Troy reviews and merges into `main`.
- Never push to `main` directly. Never force-push. Never rewrite history.
- Before committing code changes, run lint and tests (section 6). Handoff reports alone do not need them.
- Planning documents are Troy's and are not in this repository. Bob may propose changes in a handoff report.

## 9. Rules for the IBM side

- **Never commit secrets.** No API keys, Access tokens, or Orchestrate keys in files, commits, or logs. Use Code Engine secrets and local `.env` (git-ignored).
- **Do not change the security boundary** in `utils.py` or `config.py` to make a deployment work. If the server cannot reach the data API, report it; do not add proxies, alternate clients, or URL arguments.
- **Do not point the server at vaoig.gov** or any other origin. The data API is the only source.
- **Do not delete or rename shared IBM resources** that do not carry Troy's initials.
- **Do not change the `oig-data-source` side** or its hosting. That is Troy's work on his Mac.
- **Ask before** creating paid resources, changing account settings, or anything not in the phases above.
- **Keep code changes small** and limited to deployment needs. Run lint and tests before any commit, and tell Troy what changed.
- **Do not edit or delete `.agents/skills/`.**
- **Work on `ibm/` branches only.** Never push to `main` (section 8).

## 10. Open questions

These are unresolved. Do not decide them; flag anything that depends on them. The handoff lists every assumption about IBM.

1. **Availability.** Troy hosts the data API on his own machine, so the live demo depends on it and the tunnel being up. If needed, the fallback is the same API on a small cloud host behind the same Access policy, which needs no change to this server.
2. **Bearer connections in Orchestrate.** IBM's documentation conflicts on whether a remote toolkit accepts one. Phase 3 tests this first.

## 11. Reference

**Server endpoints over HTTP:** `/mcp` (MCP, streamable HTTP, stateless, JSON responses, no SSE), `/health`, `/version`.

**Transport selection:** if the platform sets `PORT` (Code Engine and the Dockerfile do), the server runs HTTP on that port. Otherwise `MCP_TRANSPORT=streamable-http` runs HTTP on `MCP_HOST:MCP_PORT`. Otherwise it runs over stdio.

**Current capabilities:**

| Name | Kind | What it returns |
|---|---|---|
| `vaoig_get_dataset_status` | Tool | Data date, counts, reconciliation with OIG, and the valid filter values |
| `vaoig_search_findings` | Tool | Ranked recommendations and corrective actions for a question in any wording. The one search tool |
| `vaoig_get_report` | Tool | One report with every recommendation and facility response |
| `vaoig_get_facility_profile` | Tool | One facility's reports, inspections, findings, and repeat findings |
| `vaoig_analyze_recommendations` | Tool | Counts, trends, time to close, and aging by year, office, topic, or report type |
| `vaoig_find_systemic_clusters` | Tool | Findings that recur across reports, and how common they are |
| `vaoig_get_inspection_brief` | Tool | One facility's history, common peer findings, peer commitments, and estimated next window |
| `vaoig://about`, `vaoig://facilities`, `vaoig://taxonomy/{facet}` | Resources | Scope and citation rules, the facility registry, and OIG's filter values |
| `inspection_readiness_checklist`, `open_recommendation_aging_brief` | Prompts | Reusable workflows |

**Glossary:**

- **OIG:** VA Office of Inspector General, which inspects and audits VA and publishes reports with recommendations.
- **Recommendation status:** `open`, `closed-implemented`, or `closed-not-implemented`.
- **HFI / CHIP:** Healthcare Facility Inspection and Comprehensive Healthcare Inspection Program, OIG's facility inspection report series.
- **VISN:** Veterans Integrated Service Network, a regional grouping of VA facilities.
- **Provenance:** the block on every response that says where the data came from and how old it is.
- **Cloudflare Access service token:** a client ID and secret sent as `CF-Access-Client-Id` and `CF-Access-Client-Secret` headers so only approved clients reach the data API.
