# Security

## Reporting a vulnerability

Please report security issues privately through GitHub's "Report a vulnerability" link on this repository's Security tab, rather than in a public issue. Include steps to reproduce and the version or commit affected.

## Design

- **One outbound origin.** The server calls only `OIG_DATA_API_BASE_URL`, set by the operator. Tool arguments never choose a host. The URL must be https unless it points at localhost, and may not carry credentials, a query, or a fragment.
- **Hardened HTTP client.** Relative paths only (absolute, encoded, and traversal paths are rejected), no redirects, environment proxies ignored, a 5 MB response cap, and a 30 second timeout.
- **Sanitized errors.** Upstream failures return a short fixed message and a hint. Response bodies, headers, URLs, and stack traces are not passed to the client or logged.
- **Credentials.** The Cloudflare Access service token for the hosted data API is read from the environment and added by the client last, so a caller cannot override it. Keep it in `.env` (git-ignored) locally and in platform secrets when deployed.
- **Public data only.** The server serves information VA OIG publishes at vaoig.gov. It handles no personal or nonpublic data.
- **The MCP endpoint.** When run over HTTP, `/mcp` has no authentication of its own. Put it behind the hosting platform's access controls for anything beyond the hackathon.

These boundaries are covered by `tests/test_http_security.py` and `tests/test_oig.py`. The outbound client design is adapted from the GSA TTS MCP hackathon template.
