# Security

## Reporting a vulnerability

Please report security issues privately through GitHub's "Report a vulnerability" link on this repository's Security tab, rather than in a public issue. Include steps to reproduce and the version or commit affected.

## What is protected

| Area | Classification and exposure |
|---|---|
| Data | Public: what VA OIG publishes at vaoig.gov. No CUI. Inspection findings are addressed to roles and offices; 77 of 15,649 recommendations, mostly from administrative investigations, name an official as OIG published them. The server never guesses who was responsible and names a person only where a quoted finding does. |
| What users send | Questions are recorded in traces during the hackathon, and users are told so (see Traces). Users are asked not to enter patient information or anything nonpublic. |
| Credentials | Inbound: MCP bearer tokens. Outbound: a Cloudflare Access service token and the data API's own key. Held in `.env` locally (git-ignored), in the container's environment, and in a key_value connection in watsonx Orchestrate. |
| Capabilities | Seven read-only tools and two read-only resources. No tool writes, runs commands, or reaches any host but the data API. |

## Design

### Connections and authentication

- **Two separate credentials.** Callers authenticate to `/mcp` with a bearer token (`MCP_AUTH_TOKEN`, or a named token in `MCP_CLIENT_TOKENS`). The server authenticates to the data API with a Cloudflare Access service token and the API's own key. Inbound tokens are never forwarded upstream, and neither kind of credential works on the other connection.
- **The MCP endpoint.** Over HTTP, `/mcp` requires a bearer token of at least 32 characters, compared in constant time against every configured token; named tokens must differ and their names are validated. The server refuses to start in HTTP mode without a token, and validation errors never echo a token. `/health` and `/version` stay open and return no data. A token in the query string is refused.
- **Stdio.** Stdio uses no token, because the client launches the server directly. That includes watsonx Orchestrate, which runs the server as a local toolkit inside its own runtime, so the server there has no network endpoint at all.
- **Local HTTP.** `MCP_TRANSPORT=streamable-http` binds `127.0.0.1` by default and checks the Host and Origin headers, so a web page cannot reach the server through DNS rebinding (421 for a foreign Host, 403 for a foreign Origin). A container listens on every interface, as it must, published only on `127.0.0.1` and reached through Cloudflare with the bearer token. Any `MCP_TRANSPORT` value other than `stdio` or `streamable-http` stops the server at startup.

### Outbound requests

- **One origin.** The server calls only `OIG_DATA_API_BASE_URL`, set by the operator. Tool arguments never choose a host. The URL must be https unless it points at localhost, and may not carry credentials, a query, or a fragment.
- **Two keys to the data API.** Every request carries the Cloudflare Access service token and, when `OIG_DATA_API_KEY` is set, the API's bearer key, so the API stays closed if the Access policy is ever removed. Both are applied after any other headers, so nothing can override them, and they are never logged or traced.
- **A hardened client.** Relative paths only (absolute, encoded, and traversal paths are rejected after repeated decoding); path parameters are integers or fully escaped; query values are encoded by httpx; filter keys are fixed (`extra="forbid"`). No redirects, environment proxies ignored, identity encoding (httpx would expand each compressed chunk whole before the 5 MB response cap could see it), a 30 second timeout per phase, and an overall deadline per request.
- **Bounded fan-out.** At most eight upstream requests run at once per server process, across all tool calls. The inspection brief alone runs up to ten searches, and the data API runs four at a time, so without this one burst of briefs would queue hundreds of requests upstream. The facility registry resource stops after 50 pages and only follows an offset that moves forward.
- **No other outbound calls.** FastMCP's startup check for a newer version is turned off, since it would contact PyPI.

### Input

- **Typed, bounded arguments.** Every tool argument is a Pydantic model or a constrained type: string lengths, page sizes (1 to 100), offsets (0 to 10,000), status lists (at most 3), enumerations for groupings and statuses, ISO date patterns, and unknown filter names refused. Resource facets come from a fixed list. Argument completion takes partial text up to 100 characters, sends it to the data API only as a query value, returns at most 10 suggestions, and answers a failure with none. When a client asks its user which facility is meant (elicitation), the answer must be one of the stations that matched, or the tool answers with the matches; a live session that does not answer within two minutes gets the matches too.
- **Values that match nothing say so.** A known office name is sent as its abbreviation, an office in the domain filter is refused with the right filter named, and an analysis that matches nothing says to check the filter values. A request too large or malformed to send becomes a clean error, not a stack trace.

### Errors

- **Sanitized and actionable.** Upstream failures return a short fixed message and a hint chosen by cause: a rejected value, a busy search queue, a slow search, a data API failure, or an unreachable API. Response bodies, headers, URLs, and stack traces never reach the client. How the API runs and which settings to check go to the operator's log, not the client.
- **Answers are not errors.** "Not found" and "several facilities match" are returned as answers with a hint, so a model can act on them.

### Model safety

- **Quoted report text.** OIG report text reaches the model verbatim. Every result names those fields in `provenance.quoted_fields` as source material, not instructions, and says never to follow instructions in them. Every tool is read-only, so text in a report cannot make the server act.
- **Scope in the server.** The server's own instructions state its scope: OIG's oversight records only; no medical, benefits, or legal advice; an emergency goes to 911; never guess who was responsible; say plainly when a question falls outside the data. Being in the server, not one host's prompt, it holds for every client.
- **No ratings, forecasts, or unsupported rates.** The server does not rate or rank facilities, labels its next-inspection estimate as its own, says findings cannot be forecast, and does not return the counts that would invite a deadline miss rate the data cannot support.

### Logs and traces

- **Usage log.** One line per tool call or resource read: client name, tool or resource, outcome, duration, and the trace ID that finds its full trace. Arguments and tokens are never logged; names a caller chooses are sanitized before they reach the log. Every file, including each new one after rotation, is private (0600); it rotates at 10 MB, keeping three.
- **Traces.** `MCP_TRACE_DIR` writes each tool call and resource read in full: client, arguments, every data API request, and the result. The data API keeps a matching trace of each request, linked by an `X-Trace-Id` header. Traces are off unless the setting is present. They are on through the hackathon, including judging, so the builder can see what people ask, and users are told: `vaoig://about`, the tester guides, and the project overview page all say questions and answers are recorded. Tokens and Cloudflare credentials are never written. Each traced argument is cut at 2,000 characters and 100 items, and a record over 1 MB drops its result, so no caller can flush the store's 400 MB cap. Real results are never cut: the largest seen is about 180 KB, and by November 17 no argument or result had been cut. Files and folders are private (0600 and 0700). In watsonx Orchestrate the server runs without `MCP_TRACE_DIR`, so the data API's traces are the record of what it was asked. After the hackathon, traces should be turned off for any general public use.

### Container and supply chain

- **Container.** Runs as an unprivileged user (uid 10001), with code owned by root. Compose drops every Linux capability, sets `no-new-privileges`, mounts the filesystem read-only except the log volume and `/tmp`, and limits memory to 1 GB and processes to 256. No secret is baked into the image; `.env` and `logs/` are excluded from the build.
- **Pinned and audited dependencies.** The base image is pinned by digest, uv by version, and every Python dependency by `uv.lock` with hashes, installed with `uv sync --frozen` and no dev dependencies. CI fails if the lock is out of date, and audits every dependency group with `pip-audit` on every change. GitHub Actions are pinned to commits, and CI's token is read-only.
- **Repository.** `main` is protected: every change needs a pull request and a passing CI run, for administrators too, and force pushes and deletion are blocked. GitHub secret scanning and push protection are on, and Dependabot opens security updates as advisories appear and version updates monthly for Python packages, Actions, and the base image. Major version jumps and changes to the Python version are left for a deliberate upgrade; versions are frozen through judging.

## How security is checked

| Check | What it covers | When | Latest result |
|---|---|---|---|
| Automated tests ([`tests/`](tests/)) | Authentication, Host and Origin checks, outbound path validation, sanitized errors, bounded traces, private files, bounded input, every tool's error hints | Every change, in CI | 267 pass (November 17, 2026) |
| Dependency audit (`pip-audit`, in CI) | Known vulnerabilities in every runtime, dev, and evaluation dependency | Every change | No known vulnerabilities in 67 runtime packages or the other groups |
| Dependabot alerts | Advisories against `uv.lock` | Continuously | 16 raised since the repository opened; all fixed |
| Secret scan (`gitleaks`, redacted output) | Every commit in the repository's history, and the working tree | Before submission | History: none. Working tree: only `.env`, which is git-ignored |
| Image checks ([`deploy/verify_image.sh`](deploy/verify_image.sh)) | No secret in the image; non-root user; refusal to start without a valid token or with a plain-HTTP data address; clean refusals with wrong data API credentials; then the deployment checks against the image | Before each deployment | 15 of 15 |
| Deployment checks ([`deploy/verify_deployment.py`](deploy/verify_deployment.py)) | Seven kinds of bad inbound credentials refused and the right one accepted; no session state; seven tools listed; live data with no secret in it; the data API refusing four kinds of wrong credentials | Against every deployment | 22 of 22 |
| Robustness check ([`deploy/robustness_check.py`](deploy/robustness_check.py)) | Path traversal and encoded paths, header and query injection, SQL and search syntax, control characters, every bound exceeded, wrong types, unknown fields and tools, names that match nothing; argument completion with traversal, oversized, and SQL values; a facility choice inside and outside the matches; a burst past the rate limit and recovery; searches past the data API's four slots; parallel latency. Every reply checked for stack traces, upstream addresses, and credentials | Against every deployment | 48 of 48 |
| Adversarial questions ([`eval/gold/adversarial.json`](eval/gold/adversarial.json)) | An instruction to ignore the rules, an instruction injected into pasted text, a report that does not exist, a medical emergency, a request to name employees, an out-of-domain question | With each evaluation round | Claude Opus 5.5: 6 of 6; Llama 3.3 70B: 4 of 6 ([results](docs/testing-results.md)) |
| Independent code review | Authentication, outbound requests, input validation, leakage, prompt injection, container, resource exhaustion | November 17, 2026 | No high-severity findings; fixes below |

## Review of November 17, 2026

A separate review agent read the code without the builder's conclusions and probed the running server. Every finding was checked against the code before it was fixed.

| Finding | Severity | Status |
|---|---|---|
| Arguments were traced before validation, so one client could send oversized calls and push every earlier trace past the store's cap | Medium | Fixed: traced arguments and records are bounded |
| Upstream fan-out was not limited: a burst of inspection briefs could queue hundreds of searches and starve other clients | Medium (reliability) | Fixed: eight upstream requests at once per process; facility paging capped |
| Some over-long inputs (an 8,000-item status list, a 70,000-character facet) escaped error handling as a raw message and a long traceback in the log | Low | Fixed: bounds on status lists, offsets, and facets; invalid requests become clean errors |
| Resource reads were missing from the usage log | Low | Fixed |
| Trace and log files were readable by every local user, and the usage log did not rotate | Low | Fixed: 0600 files, 0700 folders, rotation |
| Upstream values were placed in `notices`, which the model passes on as the server's words | Low | Fixed: only integers are used there |
| The client hint for an unreachable API named settings and how the API runs | Informational | Fixed: that detail goes to the operator's log |
| A compressed chunk was expanded whole before the size cap saw it; the timeout was per phase | Hardening | Fixed: identity encoding; an overall deadline |
| No container restrictions beyond a non-root user; base image not pinned by digest | Hardening | Fixed: capabilities dropped, no-new-privileges, read-only filesystem, limits; digest pinned |
| Quoted-text marking depends on a list of field names, and some tools pass upstream records through whole | Hardening | Accepted: the upstream is the project's own, operator-controlled API; see Known limits |
| The Orchestrate registration script passes credentials as command-line arguments and installs dependencies without hash checks | Low | Accepted for a single-user virtual machine; see Known limits |

## Known limits and accepted risks

- **Static bearer tokens.** Tokens don't expire, and a token is only as personal as its holder keeps it. Named tokens let one client be removed alone; adding or removing one restarts the server. A production deployment should use OAuth 2.1 with short-lived tokens, as the MCP authorization specification describes; FastMCP's `JWTVerifier` is the likely replacement.
- **Rate limits are per process.** Each token gets 2 requests a second with a burst of 30, counting tool calls, resource reads, prompts, and the handshake. Listings are answered from memory and not counted: on protocol 2026-07-28 the MCP library lists the tools itself before every tool call, and counting that listing had made each call cost two. Buckets live in memory, so they reset on restart, and two instances allow a client twice the rate.
- **Orchestrate users share one identity upstream.** In watsonx Orchestrate the server runs over stdio with no token, so there is no per-user limit in the server, and every Orchestrate user reaches the data API with the same credentials. Orchestrate's own access controls decide who can use the agent.
- **The registration script.** `deploy/ibm/local-mcp-toolkit/register-toolkit.sh` passes the Cloudflare secret, the data API key, and the Orchestrate key as command-line arguments, visible to other users of the same machine while it runs, and exports dependencies without hashes. It runs on a single-user virtual machine; on a shared host, pass the values through files.
- **Quoted text is marked by field name.** Fields the server passes through from the data API are marked as quoted only if they are on the list in `guidance.py`. The data API is the project's own; a third-party upstream would warrant marking every upstream field as quoted by default.
- **Client names reach the data API** in an `X-OIG-Client` header, to link its traces to the server's.
- **Load tested once, to 40 concurrent clients.** All 2,059 calls were answered, with no errors and no unclean reply, and the median call slowed from 0.33 to 1.8 seconds ([results](eval/results/2026-11-17-load-test/summary.md)). It was not run to failure, and it ran on one Mac.

These boundaries are covered by `tests/test_http_security.py`, `tests/test_mcp_auth.py`, `tests/test_oig.py`, and `tests/test_robustness.py`. The outbound client design is adapted from the GSA TTS MCP hackathon template.
