# Security

## Reporting a vulnerability

Please report security issues privately through GitHub's "Report a vulnerability" link on this repository's Security tab, rather than in a public issue. Include steps to reproduce and the version or commit affected.

## Design

- **One outbound origin.** The server calls only `OIG_DATA_API_BASE_URL`, set by the operator. Tool arguments never choose a host. The URL must be https unless it points at localhost, and may not carry credentials, a query, or a fragment.
- **Hardened HTTP client.** Relative paths only (absolute, encoded, and traversal paths are rejected), no redirects, environment proxies ignored, a 5 MB response cap, and a 30 second timeout.
- **Sanitized errors.** Upstream failures return a short fixed message and a hint. Response bodies, headers, URLs, and stack traces are not passed to the client or logged.
- **Credentials.** The Cloudflare Access service token for the hosted data API is read from the environment and added by the client last, so a caller cannot override it. Keep it in `.env` (git-ignored) locally and in platform secrets when deployed.
- **Public data only.** The server serves information VA OIG publishes at vaoig.gov. It handles no personal or nonpublic data.
- **Two separate credentials.** Callers authenticate to `/mcp` with a bearer token (`MCP_AUTH_TOKEN`). The server authenticates to the data API with a Cloudflare Access service token. The inbound token is never forwarded upstream, and neither credential works on the other connection.
- **The MCP endpoint.** Over HTTP, `/mcp` requires the bearer token, compared in constant time, and the server refuses to start without one. `/health` and `/version` stay open and return no data. Stdio does not use the token, because the local client launches the server directly.
- **Known limits.** The bearer token is one shared, non-expiring credential, rotated by replacing it on the server and in the client. That fits a read-only server over public data. It identifies no individual user. A production deployment should use OAuth 2.1 with short-lived tokens, as the MCP authorization specification describes; FastMCP's `JWTVerifier` is the likely replacement.

These boundaries are covered by `tests/test_http_security.py`, `tests/test_mcp_auth.py`, and `tests/test_oig.py`. The outbound client design is adapted from the GSA TTS MCP hackathon template.
