# Security

## Reporting a vulnerability

Please report security issues privately through GitHub's "Report a vulnerability" link on this repository's Security tab, rather than in a public issue. Include steps to reproduce and the version or commit affected.

## Design

- **One outbound origin.** The server calls only `OIG_DATA_API_BASE_URL`, set by the operator. Tool arguments never choose a host. The URL must be https unless it points at localhost, and may not carry credentials, a query, or a fragment.
- **Two keys to the data API.** Every request carries the Cloudflare Access service token and, when `OIG_DATA_API_KEY` is set, the API's own bearer key, so the API stays closed if the Access policy is ever removed. Both are applied after any caller-supplied headers, never logged or traced, and separate from the MCP tokens, which are never forwarded.
- **No other outbound calls.** FastMCP's startup check for a newer version is turned off, since it would contact PyPI.
- **Hardened HTTP client.** Relative paths only (absolute, encoded, and traversal paths are rejected), no redirects, environment proxies ignored, a 5 MB response cap, and a 30 second timeout.
- **Sanitized errors.** Upstream failures return a short fixed message and a hint. Response bodies, headers, URLs, and stack traces are not passed to the client or logged.
- **Credentials.** The Cloudflare Access service token for the hosted data API is read from the environment and added by the client last, so a caller cannot override it. Keep it in `.env` (git-ignored) locally and in platform secrets when deployed.
- **Public data only.** The server serves information VA OIG publishes at vaoig.gov. It handles no personal or nonpublic data.
- **Two separate credentials.** Callers authenticate to `/mcp` with a bearer token (`MCP_AUTH_TOKEN`, or a named token in `MCP_CLIENT_TOKENS`). The server authenticates to the data API with a Cloudflare Access service token. Inbound tokens are never forwarded upstream, and neither kind of credential works on the other connection.
- **The MCP endpoint.** Over HTTP, `/mcp` requires a bearer token, compared in constant time, and the server refuses to start without `MCP_AUTH_TOKEN`. `/health` and `/version` stay open and return no data. Stdio does not use the token, because the local client launches the server directly.
- **Local HTTP.** `MCP_TRANSPORT=streamable-http` binds `127.0.0.1` by default and checks the Host and Origin headers, so a web page cannot reach the server on a developer's machine through DNS rebinding (421 for a foreign Host, 403 for a foreign Origin). A container listens on every interface, as it must, behind Cloudflare and the bearer token. Any `MCP_TRANSPORT` value other than `stdio` or `streamable-http` stops the server at startup.
- **Quoted report text.** OIG report text reaches the model verbatim as tool output. Results name those fields in `provenance.quoted_fields` as source material, not instructions, and every tool is read-only with no write or shell ability, so text in a report cannot make the server act.
- **Usage log.** Each tool call logs the client name, tool, outcome, and duration. Tool arguments, including search questions, and tokens are never logged.
- **Test traces.** For closed testing, `MCP_TRACE_DIR` writes each tool call in full: client, arguments, every data API request, and the result. The data API keeps a matching trace of each request, linked by an `X-Trace-Id` header. Traces hold what testers asked, so they are off unless the setting is present. `compose.yaml` turns them on for the Mac, and they should be off for any public deployment. Tokens and Cloudflare credentials are never written to them.
- **Known limits.** Bearer tokens don't expire, and a token is only as personal as its holder keeps it. Named tokens let one client be removed alone, and adding or removing one restarts the server. Each token has a rate limit, kept in memory, so it resets on restart. That fits a read-only server over public data with a few trusted testers. A production deployment should use OAuth 2.1 with short-lived tokens, as the MCP authorization specification describes; FastMCP's `JWTVerifier` is the likely replacement.

These boundaries are covered by `tests/test_http_security.py`, `tests/test_mcp_auth.py`, and `tests/test_oig.py`. `deploy/verify_deployment.py` and `deploy/verify_image.sh` check them against a running server and a built image. The outbound client design is adapted from the GSA TTS MCP hackathon template.
