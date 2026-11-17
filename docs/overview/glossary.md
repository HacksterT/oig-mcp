[Wiki](../README.md) › Overview › Glossary

# Glossary

*Terms used across this wiki, in alphabetical order.*

| Term | Meaning |
|---|---|
| **Adversarial set** | Six evaluation questions that try to make the assistant misbehave: an instruction to break the rules, text injected into a quoted finding, a report that does not exist, a medical emergency, a request to name employees, and an out-of-domain question |
| **CHIP** | Comprehensive Healthcare Inspection Program, OIG's earlier facility inspection series |
| **Citation** | A report number and its vaoig.gov link. Records carry a ready-made `citation` field |
| **Cluster** | A group of recommendations that recur across reports, found by matching wording or meaning. A repeat finding is a cluster that includes the same facility more than once |
| **Closure date** | The date OIG marked a recommendation closed. It appears to record when OIG accepted the evidence, not when the work finished |
| **Data API** | The read-only JSON API over the database, built in the private `oig-data-source` repository. The server's only outbound connection. See [Data API](../architecture/data-api.md) |
| **Elicitation** | An MCP feature that lets a server ask the user a question mid-call through the host, as a form, and continue with the answer. See [MCP features](../architecture/mcp-features.md#elicitation) |
| **Facility response** | What a facility told OIG it would do about a recommendation: whether it concurred, its corrective action, and a target date. Extracted from report PDFs |
| **Gold set** | The 24 evaluation questions with answers computed by SQL from a frozen data snapshot |
| **HFI** | Healthcare Facility Inspection, OIG's current facility inspection series |
| **Host** | The application a person uses that connects to MCP servers: Claude Desktop, VS Code, Cursor, Hermes Agent, Grok, or watsonx Orchestrate |
| **MCP** | Model Context Protocol, the open standard for connecting AI applications to tools and data |
| **Notices** | Text on a result that the assistant must pass on to the user, such as a data limit |
| **OIG** | VA Office of Inspector General, which inspects and audits VA and publishes reports with recommendations |
| **Provenance** | The block on every result that says where the data came from, how old it is, how to cite it, and which fields quote report text |
| **Recommendation status** | `open`, `closed-implemented`, or `closed-not-implemented` |
| **Station number** | VA's identifier for a facility, such as 621 for the James H. Quillen VA Medical Center |
| **stdio** | The MCP transport in which the host starts the server as a local process and talks over its standard input and output |
| **Streamable HTTP** | The MCP transport over HTTP, used by the hosted endpoint at `https://mcp.troymd.com/mcp` |
| **Toolkit** | In watsonx Orchestrate, a set of MCP tools registered for agents to use. This server runs there as a local (stdio) toolkit |
| **VISN** | Veterans Integrated Service Network, a regional grouping of VA facilities. VA replaced its 18 VISNs with five on July 15, 2026, so older and newer labels can name different regions |

---

← [Mission and use cases](../overview/mission.md) · [Wiki home](../README.md) · [System](../architecture/system.md) →
