# Project Overview and Deployment Plan

**Audience:** IBM Bob, working in the IBM-provided VM on a clone of this repository, and Troy Sybert, the project owner.
**Status as of:** 2026-10-28.
**Purpose:** Explain what this project is, how its parts fit together, what already exists, and exactly what Bob should and should not do on the IBM side.

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
| `oig-data-source` | Crawls vaoig.gov, parses report pages and PDFs, builds a SQLite database, serves a JSON API over it | Troy's Mac, exposed to the internet through Troy's pilot site (planned: Cloudflare Tunnel with Cloudflare Access service tokens) | Private |
| `oig-mcp` (this repo) | The MCP server: tools, resources, prompts, evaluation | Developed on Troy's Mac; deployed to IBM Cloud Code Engine from the IBM VM; registered in watsonx Orchestrate | Public (planned) |

```
vaoig.gov (public OIG pages and PDFs)
      │  crawled by
      ▼
oig-data-source on Troy's Mac
  SQLite database ──> JSON API ──> pilot site / Cloudflare Tunnel ──> Cloudflare Access
                                                                         │
                                       HTTPS + service token headers     │
                                                                         ▼
oig-mcp on IBM Code Engine  (container from this repo's Dockerfile)
  /mcp  /health  /version
      │  streamable HTTP
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
| `oig-mcp` server foundation | Built and tested on Troy's Mac: lint clean, tests passing, `/health` and MCP `initialize` verified over HTTP |
| `vaoig_get_dataset_status` tool | Built. Calls the data API's `meta` endpoint |
| Lookup and analysis tools (`vaoig_search_findings`, `vaoig_get_report`, `vaoig_get_facility_profile`, `vaoig_analyze_recommendations`, `vaoig_find_systemic_clusters`, `vaoig_get_inspection_brief`) | Built. Facility and cluster tools are tested against a mocked API until those tables are filled |
| `vaoig://about` resource | Built. Works without the data API |
| `vaoig://taxonomy/{facet}` and `vaoig://facilities` resources, and two workflow prompts | Built. Tool-only clients get filter values from `vaoig_get_dataset_status` |
| Evaluation harness (Arize Phoenix) | Planned (F04) |
| IBM Cloud deployment | Planned (F05). This is Bob's area |
| `oig-data-source` crawler, database, and API | Live at `https://oig-api.troymd.com/v1/`. The full data build is still in progress |

The data API is live at `https://oig-api.troymd.com/v1/`, behind Cloudflare Access, so a deployment can verify live answers as well as the server, the container, Code Engine, and Orchestrate registration.

## 5. Repository tour

| Path | Contents |
|---|---|
| `src/oig_mcp/app.py` | Creates the FastMCP server, registers everything, chooses the transport |
| `src/oig_mcp/config.py` | Settings from environment variables; validates the data API URL |
| `src/oig_mcp/utils.py` | The hardened HTTP client (`fetch_json`), Access headers, provenance helper |
| `src/oig_mcp/models.py` | Pydantic models and enums: `ResponseFormat`, `RecommendationStatus`, `PaginationParams`, `Provenance` |
| `src/oig_mcp/tools/` | One file per tool; `__init__.py` registers them |
| `src/oig_mcp/resources/` | `about.py` (the `vaoig://about` resource) |
| `src/oig_mcp/prompts/` | Empty registry; prompts come with F03 |
| `src/oig_mcp/routes.py` | `/health` and `/version` HTTP routes |
| `tests/` | Security boundary tests, configuration and provenance tests, server smoke tests |
| `docs/data-api.md` | The API contract this server expects from `oig-data-source` |
| `docs/project-overview.md` | This document |
| `deploy/README.md` | Deployment notes; no deployment kit is checked in yet |
| `Dockerfile` | Python 3.11 slim image; serves streamable HTTP on port 8080 |
| `.agents/skills/` | Agent skills carried from the GSA template: `ibm-cloud-iaas-deploy`, `mcp-builder`, `mcp-eval`. Kept for Bob to assess against its own deployment skill (section 8) |
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

## 7. Bob's role and the deployment plan

Bob's job is **F05: deploy `oig-mcp` to IBM Cloud and register it in watsonx Orchestrate.** Bob's own **deployment** skill handles the mechanics (Container Registry, Code Engine, credentials). This section gives only what is specific to this project: what to deploy, how to configure it, and how to tell it worked.

**Start with the assessment assignment in section 8.** It and Phase 0 below are read-only and can be done in the same session. Phase 1 onward waits until Troy has responded to the assessment.

Work in phases. Stop and report to Troy at the end of each phase.

### What to deploy

| Item | Value |
|---|---|
| Build source | The `Dockerfile` at the repository root (Python 3.11 slim; installs the package from `pyproject.toml`) |
| Container port | `8080` (the Dockerfile sets `PORT=8080`, which switches the server to HTTP) |
| Start command | Built into the image: `python -m oig_mcp.app` |
| MCP endpoint | `/mcp` (streamable HTTP) |
| Health check | `/health`, which returns `{"status":"healthy","service":"oig-mcp"}`. There is no `/ping` |
| Version check | `/version` |
| Naming | IBM resources are shared tenants. Every image, secret, key, and app name must include Troy's initials. Ask Troy for them. Suggested: app and image `oig-mcp-<INITIALS>`, data API secret `oig-data-api-<INITIALS>` |

### Configuration

The server reads these environment variables:

| Variable | Value | Secret? |
|---|---|---|
| `MCP_AUTH_TOKEN` | Bearer token Orchestrate presents to `/mcp`. Generate a new one for IBM with `openssl rand -hex 32`. The server will not start over HTTP without it | Yes |
| `OIG_DATA_API_BASE_URL` | `https://oig-api.troymd.com/v1/` | No |
| `CF_ACCESS_CLIENT_ID` | Cloudflare Access service token ID. Troy provides it | Yes |
| `CF_ACCESS_CLIENT_SECRET` | Cloudflare Access service token secret. Troy provides it | Yes |
| `STALE_AFTER_DAYS` | `30` | No |

- Store `MCP_AUTH_TOKEN` and the two `CF_ACCESS_*` values as platform secrets, never in files or commits. They are separate credentials: the bearer token protects `/mcp`, and the Access token protects the data API.
- `OIG_DATA_API_BASE_URL` must be `https` for any non-local host; the server refuses to start with a plain `http` remote URL.
- Without the `CF_ACCESS_*` values the server still starts, but the data API rejects its requests and `vaoig_get_dataset_status` returns its "data API not reachable" hint.

### Phase 0: Verify the clone in the VM

```bash
uv sync --group dev
uv run ruff check . && uv run ruff format --check .
uv run pytest tests/ -q
export MCP_AUTH_TOKEN=$(openssl rand -hex 32)
MCP_TRANSPORT=streamable-http uv run oig-mcp     # then, in another shell:
curl http://localhost:8000/health
```

**Done when:** lint and tests pass and `/health` responds.

### Phase 1: Build and run the container locally

**Done when:** the image builds from the `Dockerfile`, runs with port 8080 mapped and `MCP_AUTH_TOKEN` set, and `/health` returns healthy. Without the token the container should exit at startup.

### Phase 2: Deploy to IBM Cloud (Bob's deployment skill)

**Done when:** the deployed app URL answers `/health` and `/version`, and an MCP `initialize` POST to `/mcp` returns the server name "VA OIG Recommendations" with the token and 401 without it. For example:

```bash
curl -s -X POST https://<APP_URL>/mcp \
  -H "Authorization: Bearer $MCP_AUTH_TOKEN" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"smoke","version":"0"}}}'
```

### Phase 3: Register in watsonx Orchestrate

Create a bearer connection holding the same token as the Code Engine secret. Orchestrate fetches `tools/list` during import, so the credentials must be set before importing:

```bash
orchestrate connections add -a oig_mcp_auth_<INITIALS>
orchestrate connections configure -a oig_mcp_auth_<INITIALS> --env draft -t team -k bearer
orchestrate connections set-credentials -a oig_mcp_auth_<INITIALS> --env draft --token <MCP_AUTH_TOKEN>
# repeat configure and set-credentials with --env live
```

IBM's documentation conflicts on this step: the remote MCP page says `--app-id` accepts only `key_value` connections, while the connections page says bearer is supported and key-value is not. If import rejects the bearer connection, stop and tell Troy.

Register the deployed `/mcp` URL as a remote MCP toolkit, named `oig_mcp_<INITIALS>`, with transport `streamable_http`, all tools, and `--app-id oig_mcp_auth_<INITIALS>`. If the ADK reports a transport mismatch, retry with the base URL without `/mcp`, or with `sse`. Suggested toolkit description: "VA OIG recommendations: dataset status and, as they are added, cross-report lookups and analytics, with citations to vaoig.gov."

Then create an agent in the Orchestrate UI that uses the toolkit, with this instruction: cite the report number and link for every finding, state the data date, and flag stale data.

**Done when:** the agent lists `vaoig_get_dataset_status`, and calling it returns live data with a `data_as_of` date.

### Phase 4: End to end, once the data API exists

When Troy reports the data API is live on the pilot site, add the configuration values above, redeploy, and ask the agent: "What is the status of the OIG dataset?" The answer should include a `data_as_of` date and counts.

**Done when:** the agent returns live data with provenance.

### Report back after each phase

Write a handoff report as described in section 8: what was done, the names created (with initials), the URLs, and anything that failed with its exact error text.

## 8. Handoff and communication

Troy develops on his Mac. Bob works in the IBM VM. GitHub is the only channel between the two copies of this repository, and written handoff reports are the record of what happened on each side.

### What Troy provides to Bob

| Item | When | How |
|---|---|---|
| Access to this repository | Before the first session | GitHub |
| Troy's initials for resource names | First session | Troy tells Bob directly |
| IBM Cloud account, resource group, and Code Engine project to use | Before Phase 2 | Troy tells Bob directly |
| watsonx Orchestrate instance URL and API key | Before Phase 3 | Entered by Troy in the VM only; never written to the repository |
| Data API URL and Cloudflare Access service token | When the data API is live (Phase 4) | Entered as platform secrets only; never written to the repository |

When Bob receives a secret, confirm receipt without repeating its value anywhere.

### Bob's first assignment: assess the repository's skills

Before any deployment work, assess the agent skills this repository carries in `.agents/skills/`, which came from the GSA hackathon template:

- `ibm-cloud-iaas-deploy`: a Container Registry and Code Engine walkthrough
- `mcp-builder`: guidance for designing MCP servers and writing evaluation questions
- `mcp-eval`: guidance for an Arize Phoenix evaluation harness

Compare them with Bob's own **deployment** skill and answer:

1. Where does `ibm-cloud-iaas-deploy` overlap with Bob's deployment skill, and where do they conflict? Check at least the health check path (`/ping` in the template skill, `/health` in this server), naming conventions, registry and image paths, and credential handling.
2. For each of the three skills: keep as is, adapt (say what to change), or remove. Give the reason.
3. Should F05 check in a deployment kit under `deploy/` (for example a script or configuration for Code Engine, or an Orchestrate local stdio toolkit)? If so, which shape, and what would it contain?
4. Anything else in this repository that will get in the way of deploying on IBM Cloud.

Do not edit or delete anything in `.agents/skills/` during the assessment. Recommend; Troy decides.

### How Bob reports back

- Write each report as a Markdown file in `docs/handoff/`, named `YYYY-MM-DD-bob-<topic>.md` (for example `2026-10-29-bob-skills-assessment.md`). Copy the structure from `docs/handoff/TEMPLATE.md`.
- One report per assignment or phase. Keep it factual: what was done, what was observed, exact error text, names and URLs created. No secrets, keys, or tokens.
- Put questions for Troy in the report's "Questions for Troy" section. If a question blocks all progress, also ask Troy directly in the session.
- Troy answers in the report's "Troy's response" section, or in a new file named `YYYY-MM-DD-troy-<topic>.md`.

### How changes move between the Mac and the VM

- At the start of every session, pull the latest `main`.
- Do all work on a branch named `ibm/<short-topic>` (for example `ibm/skills-assessment`). Commit the handoff report on that branch along with any change.
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
- **Do not edit or delete `.agents/skills/`.** Assess and recommend (section 8); Troy decides.
- **Work on `ibm/` branches only.** Never push to `main` (section 8).

## 10. Open questions

These are unresolved. Do not decide them; flag anything that depends on them.

1. **Calls out of IBM Cloud.** Troy is confirming with the organizers that a Code Engine app may call an API hosted on his own machine. If not, F05 has a fallback story (for example, a data snapshot packaged with the server).
2. **Availability.** The live demo depends on Troy's Mac and the tunnel being up. The fallback above also covers this.
3. **Deployment shape.** Code Engine with a hosted `/mcp` URL (this plan) versus Orchestrate's local stdio toolkit. The template's IBM deployment kits were removed because they did not match this server. Bob's skills assessment (section 8) informs which one F05 adds back, adapted. The template's IBM agent skill in `.agents/skills/` was kept for Bob to assess.
4. **First public push.** Whether the dataset status tool and about resource are part of the first public release is still being decided.
5. **Data API hosting.** Decided in oig-data-source (ADR-03): a Python API in a container on Troy's Mac, exposed through Cloudflare Tunnel with Access service tokens. Cloudflare D1 and a Worker are no longer planned. The organizers still need to confirm that hosting the API from a personal machine is acceptable. The API contract in `docs/data-api.md` is what this server depends on.

## 11. Reference

**Server endpoints over HTTP:** `/mcp` (MCP, streamable HTTP), `/health`, `/version`.

**Transport selection:** if the platform sets `PORT` (Code Engine and the Dockerfile do), the server runs HTTP on that port. Otherwise `MCP_TRANSPORT=streamable-http` runs HTTP on `MCP_HOST:MCP_PORT`. Otherwise it runs over stdio.

**Current capabilities:**

| Name | Kind | What it returns |
|---|---|---|
| `vaoig_get_dataset_status` | Tool | `data_as_of`, counts, reconciliation with the OIG dashboard, and `provenance`; or an error with a hint |
| `vaoig://about` | Resource | What the data is and how answers must cite it |

**Glossary:**

- **OIG:** VA Office of Inspector General, which inspects and audits VA and publishes reports with recommendations.
- **Recommendation status:** `open`, `closed-implemented`, or `closed-not-implemented`.
- **HFI / CHIP:** Healthcare Facility Inspection and Comprehensive Healthcare Inspection Program, OIG's facility inspection report series.
- **VISN:** Veterans Integrated Service Network, a regional grouping of VA facilities.
- **Provenance:** the block on every response that says where the data came from and how old it is.
- **Cloudflare Access service token:** a client ID and secret sent as `CF-Access-Client-Id` and `CF-Access-Client-Secret` headers so only approved clients reach the data API.
