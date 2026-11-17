[Wiki](../README.md) › Architecture › System

# System architecture

*How the two repositories, the hosting, and the MCP hosts fit together, end to end.*

## Two repositories

| Repository | What it does | Where it runs | Visibility |
|---|---|---|---|
| `oig-data-source` | Crawls vaoig.gov, parses report pages and PDFs, builds and checks a SQLite database, and serves a read-only JSON API over it. See [Data source](data-source.md) | One Mac, in a container, exposed through a Cloudflare Tunnel behind Cloudflare Access | Private |
| `oig-mcp` (this repository) | The MCP server: seven tools, three resources, two prompts, and the evaluation | In watsonx Orchestrate as a local toolkit; on the same Mac as a hosted endpoint; on any machine over stdio | Public |

The split keeps one concern per repository. The pipeline does the slow, careful work of turning OIG's public record into checked data; the server turns that data into answers an assistant can cite. They meet at one contract, the [Data API](data-api.md).

## Data flow

```
vaoig.gov (public OIG pages and PDFs)
      │  crawled politely, then parsed, checked, and indexed
      ▼
oig-data-source: SQLite database ──> read-only JSON API
      │  HTTPS through Cloudflare Tunnel and Access: service token + API key
      ▼
oig-mcp: 7 tools · 3 resources · 2 prompts · auth · rate limit · usage log · traces
      │  stdio                                   │  Streamable HTTP
      ▼                                          ▼
watsonx Orchestrate, Claude Desktop,      https://mcp.troymd.com/mcp
VS Code, Cursor, Grok                      remote agents, testers, the evaluation harness
      │
      ▼
The person asking, with a report number and link for every finding
```

The server calls exactly one outbound origin, the data API set by the operator in `OIG_DATA_API_BASE_URL`. It never fetches vaoig.gov or any other site, and no tool argument can change where it connects. Every query the API runs is written ahead of time with bound values: neither the server nor a model writes SQL.

## Transports

The same server runs over both standard MCP transports; only how a host starts it differs.

| Transport | Used by | How it runs |
|---|---|---|
| stdio | watsonx Orchestrate, Claude Desktop, VS Code, Cursor, Grok | The host starts the server as a local process. No network endpoint, no token |
| Streamable HTTP | Remote agents, testers, the evaluation harness | The container serves `/mcp`, `/health`, and `/version`, behind a bearer token per client |

Over HTTP the server keeps a session per client and streams its replies, so it can ask the user a question mid-call on every protocol version. A call without a session is still answered the stateless way, so a client that never holds a session keeps working. Idle sessions close after 30 minutes. Transport selection: a platform-set `PORT` (as in the container) runs HTTP on all interfaces; `MCP_TRANSPORT=streamable-http` runs it on loopback with Host and Origin checks; otherwise the server runs over stdio. Setup for each host: [Connecting](../guides/connecting.md).

## Where it is deployed

- **watsonx Orchestrate.** Registered from an IBM-provided virtual machine as a local (stdio) toolkit. Orchestrate runs the server inside its own runtime and passes the data API's settings from a key_value connection. The agent `gsa-oig-assist-TES` uses the seven tools with one instruction: answer only from what the tools return. IBM Code Engine was planned and not used, because the account had none set up.
- **Hosted endpoint.** The same container image runs on the Mac that hosts the data API, reachable at `https://mcp.troymd.com/mcp` through its own Cloudflare Tunnel, with a bearer token per tester and tool-call traces on through judging.

Running and checking both: [Deployment](../guides/deployment.md).

## Availability

The data API and the hosted endpoint run on one machine, so both depend on it and its tunnel being up. Each build is a dated snapshot with checksums, so the API can move to a small cloud host behind the same Access policy with no change to this server.

---

← [Glossary](../overview/glossary.md) · [Wiki home](../README.md) · [Data source](../architecture/data-source.md) →
