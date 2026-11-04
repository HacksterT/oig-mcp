# Deployment handoff: oig-mcp to IBM Code Engine and watsonx Orchestrate

**Author:** Troy Sybert, with Claude Code
**Date:** 2026-11-04
**Assignment:** F05, deploy and register
**Branch for your work:** `ibm/deploy`

## Summary

The server is built, tested, and evaluated on Troy's Mac. Your job is to run the same image on Code Engine, register it in Orchestrate, and tell Troy which assumptions below were wrong. Nothing here has run on IBM yet, so the assumptions are real risks, and the first checks are ordered to find bad ones early.

Read this first, and then [`docs/project-overview.md`](../project-overview.md) for the project and its rules. Where your own skills differ on something specific to this project, these documents win. If you need a value that is not here, ask Troy. Do not guess, and do not change the server's authentication or outbound rules to get past a problem. Stop and report it.

## What you get from Troy

| Item | Notes |
|---|---|
| Repository access | The repository will be public, so cloning needs no credentials. Pushing `ibm/` branches does (assumption A1) |
| Initials | `TES`. Required in every IBM resource name |
| IBM account, resource group, Code Engine project | Assumption A5 |
| Orchestrate instance URL and API key | Entered in the VM, never written to a file in the repository |
| `OIG_DATA_API_BASE_URL`, `CF_ACCESS_CLIENT_ID`, `CF_ACCESS_CLIENT_SECRET` | Provided directly. Treat all three as secrets, although the URL is not strictly one |

You generate `MCP_AUTH_TOKEN` yourself with `openssl rand -hex 32`. Use a new one for IBM, not one from the Mac. Confirm you have received secrets without repeating their values, and never put them in commits, logs, command arguments that get logged, or handoff reports.

## How authentication works

There are two separate credentials, and neither works on the other's connection.

```
Orchestrate agent
   |  HTTPS, Authorization: Bearer <MCP_AUTH_TOKEN>
   |  Stored in: Orchestrate connection, and a Code Engine secret
   v
oig-mcp on Code Engine
   |  HTTPS, CF-Access-Client-Id and CF-Access-Client-Secret
   |  Stored in: a Code Engine secret only. Orchestrate never sees it
   v
Cloudflare Access, then the OIG data API on Troy's machine
```

The bearer token is the only authentication built. OAuth is not. It is one shared token that does not expire, which is acceptable for a read-only server over public data, and `SECURITY.md` records that limit. It is rotated by changing it in both places, then restarting the app.

## What is tested, and how

| Check | Where it ran | Result |
|---|---|---|
| Unit tests and lint | Mac | 120 tests pass |
| Image builds for `linux/amd64` and imports the package | Mac, under emulation | Pass. It has not run a full request cycle on amd64 |
| Refuses to start without a token, with a short token, or with a plain-HTTP remote API | Container | Pass |
| Both connections accept right and refuse wrong credentials: 21 checks | Container, and through a public HTTPS tunnel | Pass |
| Missing or wrong Cloudflare token gives a clean refusal without the API address | Container | Pass |
| No secret in the image, tool responses, or logs | Container | Pass |
| An independent MCP client with a different model answers the questions | Hermes Agent running DeepSeek V4 Pro 0813, through the tunnel | Facts all correct. It gave report numbers but no links, which led to the citation field described in D10 |
| 24 gold questions, on two Claude models | Container | 23 of 24 each. See [`docs/evaluation.md`](../evaluation.md) |

**Not tested at all:** IBM's network, Code Engine, Orchestrate's import, its connections, and its model.

## Assumptions about the IBM environment

"Basis" says how much to trust each one. **Docs** means IBM's documentation says so. **Code** means Troy's team read IBM's ADK source. **Template** means the hackathon's skill in `.agents/skills/ibm-cloud-iaas-deploy/` says so. **Assumed** means nobody has checked.

Report each one as confirmed or wrong in your phase reports.

### The VM and tools

| # | Assumption | Basis | If wrong |
|---|---|---|---|
| A1 | The VM can reach GitHub and clone the public repository. Push access to `ibm/` branches is arranged with Troy | Assumed | Troy supplies a zip. Reports come back through Troy instead of a branch |
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
| B6 | The default request timeout of 300 seconds is enough. The slowest tool took about 4 seconds | Docs, and measured on the Mac | Report it |
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
| D6 | The tool schemas import. None use `$ref`, but four use `anyOf` for optional fields, and two take a nested filter object. Tool names use only letters and underscores | Assumed. The ADK validates them, and no one has run that | Send Troy the exact error and the tool name |
| D7 | Orchestrate calls tools with a timeout of about 2 minutes. MCP has no asynchronous mode there | Docs, in the Tool Performance Guide | Should not matter at about 4 seconds or less per tool |
| D8 | No response size limit gets in the way. IBM documents none. The largest response seen was about 90,000 characters, from a facility profile with 100 recommendations. Others stayed under about 40,000 | No documented limit | If responses fail or are cut off, record which tool and which facility. `vaoig_get_facility_profile` accepts a smaller `limit`, and Troy decides on the default |
| D9 | MCP prompts and resources do not import, only tools. IBM's page is silent. The tools carry what is needed, and `vaoig_get_dataset_status` returns the filter values | Assumed | No change needed. Good news if they do import |
| D10 | Orchestrate may not pass the server's `instructions` to its model. Hermes Agent appears not to, and left links out of its answers. So each tool result now carries a `provenance.citation` line saying how to cite it | Hermes observed. Orchestrate unknown | See Phase 4 |
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

Put the four settings from `deploy/README.md` in a local `.env`, which git ignores, and then:

```bash
deploy/verify_image.sh
```

Set `CONTAINER_ENGINE=podman` if it picks the wrong one. **Done when:** every check passes. This is also the first test of the path from the VM to Cloudflare, though not from Code Engine. Record the result for C2 and C3 either way.

### Phase 2: deploy to Code Engine

Use your deployment skill for the registry and registry secret, with initials in every name. The project-specific part:

```bash
# Write the three secret values to a file outside the repository, readable only by you.
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

The secret file holds `MCP_AUTH_TOKEN`, `OIG_DATA_API_BASE_URL`, `CF_ACCESS_CLIENT_ID`, and `CF_ACCESS_CLIENT_SECRET`. Delete it afterward. Then, from the VM:

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

If answers lack citations or drop caveats (D10), report that to Troy with the answers before adding anything to the agent. If he agrees, the most this project expects is one line: cite the report number and link for each finding, state the data date, and pass on any caveat a tool returns. Do not put domain steps or logic into the agent's instructions.

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

1. How should Bob push `ibm/` branches from the VM (A1)?

## Troy's response

(Troy fills this in.)
