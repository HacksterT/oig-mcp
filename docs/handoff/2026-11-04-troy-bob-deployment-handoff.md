# Deployment handoff: oig-mcp to IBM Code Engine and watsonx Orchestrate

**Author:** Troy Sybert, with Claude Code
**Date:** 2026-11-04, updated 2026-11-10
**Assignment:** F05, deploy and register
**Branch for your work:** `ibm/deploy`

## Summary

The server is built, tested, and evaluated on Troy's Mac. Your job is to run the same image on Code Engine, register it in Orchestrate, and tell Troy which assumptions below were wrong. Nothing here has run on IBM yet, so the assumptions are real risks, and the first checks are ordered to find bad ones early.

Read this first, and then [`docs/project-overview.md`](../project-overview.md) for the project and its rules. Where your own skills differ on something specific to this project, these documents win. If you need a value that is not here, ask Troy. Do not guess, and do not change the server's authentication or outbound rules to get past a problem. Stop and report it.

## What changed since 2026-11-04

If you read an earlier copy, these are the differences that affect you:

- **A fifth secret.** The data API now checks its own key behind Cloudflare Access, so `OIG_DATA_API_KEY` goes in the Code Engine secret with the other four. The Access token alone is refused.
- **The repository is public.** Cloning needs no access.
- **Typed results.** Each tool now publishes an output schema, and four of them allow more than one result shape. Orchestrate's import has not seen these yet (D6).
- **Search limits on the data API.** It runs four searches at once and queues the rest. A tool can answer that the API is busy (429) or that a search took too long (503). Neither is a deployment failure.
- **Tracing stays on through judging.** Do not set `MCP_TRACE_DIR` on Code Engine until Troy decides where traces go (Phase 2).
- **`deploy/verify_image.sh` now passes the API key** to its test container. An older copy fails Phase 1 against today's API.

## What you get from Troy

| Item | Notes |
|---|---|
| Repository access | The repository is public as of 2026-11-10, so cloning needs no access. Pushing `ibm/` branches still needs access from Troy (assumption A1). |
| Initials | `TES`. Required in every IBM resource name |
| IBM account, resource group, Code Engine project | Assumption A5 |
| Orchestrate instance URL and API key | Entered in the VM, never written to a file in the repository |
| `OIG_DATA_API_BASE_URL`, `CF_ACCESS_CLIENT_ID`, `CF_ACCESS_CLIENT_SECRET`, `OIG_DATA_API_KEY` | Provided directly. Treat all four as secrets, although the URL is not strictly one. Troy refreshes the Cloudflare token before handing it over, because earlier testing exposed part of it. Use only the values he gives you, and nothing from older notes |

You generate `MCP_AUTH_TOKEN` yourself with `openssl rand -hex 32`. Use a new one for IBM, not one from the Mac. Confirm you have received secrets without repeating their values, and never put them in commits, logs, command arguments that get logged, or handoff reports.

## How authentication works

There are two separate credentials, and neither works on the other's connection.

```
Orchestrate agent
   |  HTTPS, Authorization: Bearer <MCP_AUTH_TOKEN>
   |  Stored in: Orchestrate connection, and a Code Engine secret
   v
oig-mcp on Code Engine
   |  HTTPS, CF-Access-Client-Id and CF-Access-Client-Secret,
   |  and Authorization: Bearer <OIG_DATA_API_KEY>
   |  Stored in: a Code Engine secret only. Orchestrate never sees it
   v
Cloudflare Access, then the OIG data API on Troy's machine
```

The bearer token is the only authentication built. OAuth is not. It is one shared token that does not expire, which is acceptable for a read-only server over public data, and `SECURITY.md` records that limit. It is rotated by changing it in both places, then restarting the app.

### Changing a token

| Token | Who changes it | Steps | What happens meanwhile |
|---|---|---|---|
| `MCP_AUTH_TOKEN` | Bob or Troy | Generate a new one. Update the Code Engine secret and restart the app (B3). Run `orchestrate connections set-credentials` with the new token for both `draft` and `live` | Orchestrate's calls get a 401 until both places match |
| Cloudflare token | Troy, in the Cloudflare dashboard | Troy refreshes it, which ends the old one at once. Update the Code Engine secret and restart the app. Orchestrate needs no change | Tools return a refusal until the app restarts. Avoid this during judging. It expires after one year by default |
| `OIG_DATA_API_KEY` | Troy, on the data API side | Troy changes it there and gives you the new value. Update the Code Engine secret and restart the app. Orchestrate needs no change | Tools return a refusal until the app restarts |

### What an auth failure looks like

| What you see | Likely cause | What to do |
|---|---|---|
| A 401 from `/mcp` | The bearer token does not match the Code Engine secret, or the secret has not reached the app | Compare by setting a new token in both places. Do not print it |
| The app exits at startup, with `MCP_AUTH_TOKEN must be set`, or fails on a token under 32 characters | The secret is missing, not attached, or too short | Check `--env-from-secret`, then the secret's keys |
| The app exits at startup over `OIG_DATA_API_BASE_URL` | The URL is not `https` | Use the value from Troy, ending in `/v1/` |
| Tools return `Upstream service returned status 401` | The Cloudflare token or `OIG_DATA_API_KEY` is wrong, missing, or has been changed | Ask Troy for the current values |
| A tool answers that the data API is busy (status 429), or that the search took too long (status 503) | The API's search limits: four at once, a 10 second queue, a 2 second full-text limit | Not a deployment failure. Wait a few seconds and try again, and report it only if it persists |
| Tools return status 403, or a request failure | IBM's network or a Cloudflare setting (C2, C3), or the API is down (C4) | Report the exact text to Troy. Do not add a proxy |
| Orchestrate's import fails with a 4xx | The connection's token is wrong, or it rejects a bearer connection (D2, D4) | Check with `verify_deployment.py` first. If that passes, stop and send Troy the exact error |

## What is tested, and how

| Check | Where it ran | Result |
|---|---|---|
| Unit tests and lint | Mac, and a fresh clone | 193 tests pass (2026-11-10) |
| Image builds for `linux/amd64` and imports the package | Mac, under emulation | Pass. It has not run a full request cycle on amd64 |
| `deploy/verify_image.sh`, your Phase 1 | Mac, 2026-11-10 | 15 checks pass, including the 22 below run against the built image |
| Refuses to start without a token, with a short token, or with a plain-HTTP remote API | Container | Pass |
| Both connections accept right and refuse wrong credentials: 22 checks, including the data API refusing the Access token without its key | Container, and through a public HTTPS tunnel | Pass |
| Missing or wrong Cloudflare token gives a clean refusal without the API address | Container | Pass |
| No secret in the image, tool responses, or logs | Container | Pass |
| An independent MCP client with a different model answers the questions | Hermes Agent running DeepSeek V4 Pro 0813, through the tunnel | Facts all correct, 18 questions. Its answers named reports but gave almost no links, under test instructions that may have caused that. See D10 |
| 24 gold questions, on two Claude models | Container | 23 of 24 each, and Opus again on 2026-11-10 after the last changes, with the same scores. See [`docs/evaluation.md`](../evaluation.md) |

**Not tested at all:** IBM's network, Code Engine, Orchestrate's import, its connections, and its model.

## Assumptions about the IBM environment

"Basis" says how much to trust each one. **Docs** means IBM's documentation says so. **Code** means Troy's team read IBM's ADK source. **Template** means the hackathon's skill in `.agents/skills/ibm-cloud-iaas-deploy/` says so. **Assumed** means nobody has checked.

Report each one as confirmed or wrong in your phase reports.

### The VM and tools

| # | Assumption | Basis | If wrong |
|---|---|---|---|
| A1 | The VM can reach GitHub to clone this public repository, and Troy arranges access to push `ibm/` branches. Treat that credential like any other secret | Assumed | Troy supplies a zip. Reports come back through Troy instead of a branch |
| A2 | The VM has `podman` or `docker`. The template's commands use `podman` and a `Containerfile`. This repository has a `Dockerfile`, so pass `-f Dockerfile` | Template | Report it. Code Engine can also build from source, but do not switch without asking |
| A3 | The VM can pull `docker.io/library/python:3.11-slim` and reach PyPI during the build. The base image no longer needs `ghcr.io` | Assumed | Report the exact error. A mirror may be needed |
| A4 | The VM is `linux/amd64`, or images get built for it | Assumed | Build with `--platform linux/amd64` |
| A5 | Account `itz-saas-<NNN>`, and resources are shared, so every name carries Troy's initials. The registry is `us.icr.io`, in namespace and resource group given by the personalized helper script | Template | Ask Troy |
| A6 | Code Engine pulls from `private.us.icr.io`, not `us.icr.io`, with a registry secret | Template | Try the other, and report which worked |
| A7 | `uv` can be installed in the VM for the checks in this repository | Assumed | `pip install uv`, or run the check script with any Python that has `httpx` and `fastmcp` |
| A8 | `ibmcloud`, the Container Registry and Code Engine plugins, and the Orchestrate ADK can be installed if missing | Template, for the first two | Ask Troy |

### Code Engine

| # | Assumption | Basis | If wrong |
|---|---|---|---|
| B1 | It sets `PORT`, and apps listen on `8080` by default. The image also sets `PORT=8080` | Docs | Set `--port 8080` explicitly anyway |
| B2 | Public URL on HTTPS 443, with TLS handled by the platform. The server itself speaks HTTP | Docs | Report it |
| B3 | Secrets reach the app as environment variables through `--env-from-secret`, and a changed secret needs a restart or new revision | Docs | Report it |
| B4 | One instance staying up (`--min-scale 1`) is allowed. Orchestrate's import gives the server 30 seconds, so a cold start is a risk with zero | Template uses it. Default is zero | If not allowed, warm the app with `/health` before importing, and report it |
| B5 | Default resources, 1 vCPU and 4 GB, are more than needed. The image is about 260 MB | Docs for the default | If quota is tight, try 0.25 vCPU and 1 GB. This is unmeasured |
| B6 | The default request timeout of 300 seconds is enough. The slowest tool, the inspection brief, takes about 2 seconds. A search can wait up to about 23 seconds when the API's search slots are full | Docs, and measured on the Mac | Report it |
| B7 | Running more than one instance is safe. The server is stateless, with no sessions | Tested on the server's side | Not an IBM risk |

### Reaching the data API

| # | Assumption | Basis | If wrong |
|---|---|---|---|
| C1 | The data API stays on Troy's machine, which is his decision. A Code Engine app can call it like any public HTTPS service | Troy's decision. Not yet run from IBM | Tell Troy. The fallback is the same API on a cloud host behind the same Access policy, needing no change here |
| C2 | Code Engine's outbound traffic reaches Cloudflare, with no allowlist or proxy needed. The HTTP client ignores proxy settings by design, and must keep doing so | Assumed | Report the exact tool error. Do not add a proxy |
| C3 | Cloudflare admits IBM's addresses. The Access policy is service token only, with no IP rule, but any bot or firewall setting on the zone has not been tested against a datacenter address | Assumed for the bot rules | A tool returning status 403, or an error where `verify_deployment.py` passes on the Mac, points here. Tell Troy, who controls Cloudflare |
| C4 | The data API is up. It runs on one machine, so it can go down, and tools then return an error with a hint | Known | Tell Troy. Do not treat this as a deployment failure |

### watsonx Orchestrate

| # | Assumption | Basis | If wrong |
|---|---|---|---|
| D1 | The ADK is 2.x, where the command is `orchestrate toolkits add`. Before 2.0 it was `toolkits import`. Version 2.19.1 was the latest read | Docs and code | Check `orchestrate --version`, and adapt the command name |
| D2 | **A remote toolkit accepts a bearer connection on `--app-id`. This is the most likely problem.** IBM's remote MCP page says only `key_value`. Its connections support table lists bearer for remote MCP. ADK 2.19.1's help text says "Only type key_value is currently supported for STDIO MCP," which suggests the restriction is for local toolkits | Conflicting docs. Code favors bearer | Stop and tell Troy, with the exact error. A `key_value` connection is a possible route, but nobody has confirmed that its values become HTTP headers. The server accepts only `Authorization: Bearer`, so do not change that without Troy |
| D3 | A `team` connection, configured and given credentials for both `draft` and `live`, is correct for one shared token | Docs | Report it |
| D4 | Import calls `tools/list` with those credentials within 30 seconds, without running tools, and a 4xx fails the import. So deploy, verify, and set credentials before importing | Docs | Report it |
| D5 | Transport is `streamable_http` with the URL ending in `/mcp`. **Do not try `sse`: this server has no SSE.** A `GET` to `/mcp` correctly returns 405, and POST responses are plain JSON | Tested on the server's side. Docs say the ADK will not switch protocols | Report the exact error. Do not change the server's transport without asking |
| D6 | The tool schemas import. Input schemas use no `$ref`; several use `anyOf` for optional fields, and two take a nested filter object. Every tool also publishes an output schema, with no `$ref`. Four of them (`vaoig_get_report`, `vaoig_get_facility_profile`, `vaoig_find_systemic_clusters`, `vaoig_get_inspection_brief`) have an `anyOf` at the top level, because they can answer "not found" or "several match" as well as with data. Tool names use only letters and underscores | Assumed. The ADK validates them, and no one has run that. The output schemas are the newer risk | Send Troy the exact error and the tool name. Do not edit the schemas to get past it |
| D7 | Orchestrate calls tools with a timeout of about 2 minutes. MCP has no asynchronous mode there | Docs, in the Tool Performance Guide | Should not matter: tools take about 2 seconds or less, and about 23 at worst when searches queue |
| D8 | No response size limit gets in the way. IBM documents none. The largest response seen was about 90,000 characters, from a facility profile with 100 recommendations. Others stayed under about 40,000 | No documented limit | If responses fail or are cut off, record which tool and which facility. `vaoig_get_facility_profile` accepts a smaller `limit`, and Troy decides on the default |
| D9 | MCP prompts and resources do not import, only tools. IBM's page is silent. The tools carry what is needed, and `vaoig_get_dataset_status` returns the filter values | Assumed | No change needed. Good news if they do import |
| D10 | Orchestrate may not pass the server's `instructions` to its model. Hermes Agent appears not to. So each tool result carries a `provenance.citation` line saying how to cite it, and a `notices` list of what to pass on. Hermes' answers still had almost no links, though its test format may be why | Hermes observed. Orchestrate unknown | See Phase 4 |
| D11 | Orchestrate's outbound traffic can reach a Code Engine public URL | Assumed | Report the exact error |
| D12 | A `409 Gateway name already exists` after deleting a toolkit is a known leftover. Use a new unique name | Docs | |

## Steps

Stop and report at the end of each phase, using `docs/handoff/TEMPLATE.md`, in a file named `YYYY-MM-DD-bob-<topic>.md`. Work on `ibm/` branches, and never push to `main`.

### Phase 0: verify the clone

```bash
uv sync --group dev
uv run ruff check . && uv run ruff format --check .
uv run pytest tests/ -q
```

**Done when:** all pass. The `eval` dependency group is heavy, and you do not need it.

### Phase 1: build and check the image

Put the settings from `deploy/README.md` in a local `.env`, which git ignores: the five secrets, including `OIG_DATA_API_KEY`. Then:

```bash
deploy/verify_image.sh
```

Set `CONTAINER_ENGINE=podman` if it picks the wrong one. **Done when:** every check passes. This is also the first test of the path from the VM to Cloudflare, though not from Code Engine. Record the result for C2 and C3 either way.

### Phase 2: deploy to Code Engine

Use your deployment skill for the registry and registry secret, with initials in every name. The project-specific part:

```bash
# Write the five settings below to a file outside the repository, readable only by you.
ibmcloud ce secret create --name oig-mcp-secrets-TES --from-env-file <file>

ibmcloud ce application create \
  --name oig-mcp-TES \
  --image private.us.icr.io/<NAMESPACE>/oig-mcp-TES:latest \
  --registry-secret <REGISTRY_SECRET> \
  --port 8080 \
  --min-scale 1 \
  --max-scale 2 \
  --env-from-secret oig-mcp-secrets-TES
```

The secret file holds `MCP_AUTH_TOKEN`, `OIG_DATA_API_BASE_URL`, `CF_ACCESS_CLIENT_ID`, `CF_ACCESS_CLIENT_SECRET`, and `OIG_DATA_API_KEY` (the data API's own key, added 2026-11-10; never print it). Delete it afterward, and delete the `.env` from Phase 1 when you finish deploying.

Rate limits are kept per instance, so with `--max-scale 2` a client's effective limit is up to twice the configured one: 4 requests a second, burst 60. That is acceptable for a few trusted testers and judges. Use `--max-scale 1` if the configured limit must hold exactly.

Troy keeps full tool-call traces on through judging, so he can see what people ask. Code Engine app storage is temporary and separate per instance, so traces written inside the container would be lost. Do not set `MCP_TRACE_DIR` until Troy decides where traces go on IBM; ask him in your Phase 2 report.

Then, from the VM:

```bash
export MCP_AUTH_TOKEN=<the same token>
uv run python deploy/verify_deployment.py --url https://<APP_URL>
```

**Done when:** it reports no failures. The "MCP server to data API" group is the first real test of C1, C2, and C3. If it fails there, get the exact tool error from the script's output and from `ibmcloud ce application logs`, and stop.

### Phase 3: register in Orchestrate

Test D2 first, because everything else waits on it.

```bash
orchestrate connections add -a oig_mcp_auth_TES
orchestrate connections configure -a oig_mcp_auth_TES --env draft -t team -k bearer
orchestrate connections set-credentials -a oig_mcp_auth_TES --env draft --token <MCP_AUTH_TOKEN>
orchestrate connections configure -a oig_mcp_auth_TES --env live -t team -k bearer
orchestrate connections set-credentials -a oig_mcp_auth_TES --env live --token <MCP_AUTH_TOKEN>

orchestrate toolkits add \
  --kind mcp \
  --name oig_mcp_TES \
  --description "VA OIG reports and recommendations: search, facility history, closure measures, recurring findings, and inspection preparation, cited to vaoig.gov." \
  --url https://<APP_URL>/mcp \
  --transport streamable_http \
  --tools "*" \
  --app-id oig_mcp_auth_TES
```

The token on the command line may land in your shell history. Clear it or use a method your skill prefers. **Done when:** the import succeeds, and all seven tools are listed.

### Phase 4: the agent, and end to end

Create an agent in Orchestrate that uses the toolkit, **with no project-specific instructions at first.** A core decision of this project is that the behavior lives in the server, so any assistant can use it. The server's tool descriptions are meant to be enough.

Ask these, in order, and put each full answer in your report:

| # | Question | What a good answer does |
|---|---|---|
| 1 | What is the status of the OIG dataset? | Gives data as of 2026-11-04, with 4,415 report listings and 15,649 recommendations, unless Troy says the data was rebuilt again |
| 2 | How many recommendations did OIG make in Healthcare Facility Inspection reports published in 2026, and how many are still open? | 148 and 80 |
| 3 | On rounds I saw staff leave medication carts unlocked in a hallway. Has OIG cited this kind of thing? Point me to the reports. | Says yes, with report numbers and vaoig.gov links |
| 4 | I manage quality at the VA El Paso Healthcare System. Help me prepare for our next OIG inspection. | Uses `vaoig_get_inspection_brief`. Labels the next window as an estimate, and does not predict findings |
| 5 | What has OIG found at the New York VA? | Says several facilities match, rather than picking one |
| 6 | What percentage of VHA recommendations missed their target completion dates? | Gives no percentage, and explains that the data cannot establish it |

If answers lack citations or drop caveats (D10), report that to Troy with the answers before adding anything to the agent. If he agrees, the most this project expects is one line: cite the report number and link for each finding, state the data date, and pass on every entry in a tool's notices. Do not put domain steps or logic into the agent's instructions.

These answers come from Orchestrate's model, not the Claude models in the evaluation, so differences are useful findings. Report them as they are.

**Done when:** the six questions are answered and reported. Troy will then ask whether to run the full evaluation against the deployed URL, which needs an Anthropic key and is run with `eval/phoenix/run_experiment.py --url https://<APP_URL>`.

## Skills in this repository

`.agents/skills/` holds skills from the hackathon template. No assessment is needed. Do not edit them. Where `ibm-cloud-iaas-deploy` differs from this server, this document wins:

| Template skill says | This server |
|---|---|
| Health check at `/ping` | `/health` |
| `Containerfile` | `Dockerfile` |
| Image names like `gsa-jmd-mcp-app` | `oig-mcp-TES` |
| `cat` the API key file to read it | Do not print secrets |
| Deploy with no app environment | Needs `--env-from-secret` |

`mcp-builder` and `mcp-eval` were for building the server and evaluation, and are finished with.

## Things not to change

The rules in `docs/project-overview.md` section 9 apply. The ones most likely to tempt you:

- Do not add a proxy, another HTTP client, or a URL argument to reach the API.
- Do not open `/mcp`, weaken the token check, or bring back SSE to make an import work.
- Do not touch the data API or its hosting. That is Troy's.
- Do not delete or rename IBM resources without Troy's initials.
- Ask before creating anything paid that is not listed here.

## Questions for Troy

1. How does Bob get access to push `ibm/` branches from the VM (A1)? Cloning needs none, since the repository is public.
2. Where should tool-call traces go on Code Engine, since its storage is temporary: a mounted volume, object storage, a log sink, or nowhere on IBM (Phase 2)?

## Troy's response

(Troy fills this in.)
