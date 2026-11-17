[Wiki](../README.md) › Guides › Decisions

# Decisions

*The design decisions that shape the project, each with what was chosen, why, and what it costs. Newest server decisions last.*

## Server

**Seven goal-oriented tools, not one per API endpoint.** Each tool answers a task a user has; several combine many data requests. *Why:* fewer calls means fewer mistakes, and a weaker model fails when it must sequence ten calls itself. *Cost:* each tool is larger and has more to document.

**Guardrails in the server, not in a host's prompt.** Citation rules, scope, notices, and refusals travel in the server's instructions and results. *Why:* they then hold for every host and model, including an Orchestrate agent with a single instruction. *Cost:* results are longer.

**Finding and counting are separate.** Search returns a ranked shortlist, never a count; every count is an exact database query. *Why:* a shortlist has no natural end, so a count from it would be wrong. *Cost:* a model must choose the right tool, so every description says which.

**No ratings or rankings.** Facility is not a grouping, and nothing scores a facility. *Why:* the records support comparisons of findings, not judgments of facilities. *Cost:* some leaders' questions are declined.

**No computed miss rate for target dates.** The analysis tool leaves out closed-after-target counts. *Why:* a target is the facility's estimate and a closure date appears to record OIG's closure, so a miss rate would mislead. *Cost:* a frequently asked number is not offered.

**VISN labels kept as OIG published them, with a warning.** *Why:* VA replaced its 18 VISNs with five on July 15, 2026, and OIG did not retag older reports, so some labels name two regions; rewriting OIG's labels would invent data. *Cost:* every VISN filter carries a notice and points to state instead.

**One outbound origin.** The server reaches only the operator-configured data API, with relative paths. *Why:* no tool argument or report text can redirect it. *Cost:* the server cannot fetch anything the API does not serve.

**Watsonx Orchestrate through a local (stdio) toolkit, not Code Engine.** *Why:* the hackathon account had no Code Engine setup; a local toolkit runs the same server inside Orchestrate with no public address. *Cost:* the toolkit must be re-imported, and its tools re-added to the agent, after every server change.

**A hosted endpoint on the same machine as the data API, behind Cloudflare.** *Why:* testers and the evaluation need an HTTP endpoint, and Cloudflare Tunnel and Access expose it without an open port. *Cost:* one machine is a single point of failure; a dated snapshot allows a move to a cloud host with no server change.

**Ambiguous facility names are asked about, never guessed** ([#92](https://github.com/HacksterT/oig-mcp/pull/92)). Unless a name is exact, the lookup also searches the place alone and as a state, and several matches return a list with a next step: do not choose, ask. *Why:* real hosts chose a facility for "the New York VA", and findings from the wrong facility would be credited to the right one. A name that ends in a state, such as "Columbia SC" or "Columbia, South Carolina", is looked up in that state; "VA" is always read as Veterans Affairs, never Virginia. When the user chooses in the server's form, the result says so, because the model cannot see the form. *Cost:* an ambiguous name always costs one extra turn.

**HTTP sessions, but optional** ([#101](https://github.com/HacksterT/oig-mcp/pull/101), [#103](https://github.com/HacksterT/oig-mcp/pull/103)). The hosted endpoint keeps a session per client and answers a call without one the stateless way. *Why:* without sessions it could ask only clients on protocol 2026-07-28; making sessions required broke a real client that never held one. *Cost:* sessions live in memory and end on a restart, so compliant clients reconnect.

**The scorer is never loosened after seeing a result.** *Why:* a scorer changed to fit an answer measures nothing. *Cost:* some correct answers stay failures, such as "agreed" where the check looks for "concur".

## Data source

**No AI in the data path.** Facility responses are extracted by rules, not a language model, and embeddings run locally. *Why:* deterministic, checkable extraction, and no report text leaves the machine. *Cost:* lower coverage on report types without a consistent format.

**SQLite as the system of record, built and published as a dated snapshot.** *Why:* one file, checksummed, that a build either fully replaces or does not touch. *Cost:* one writer at a time, which a weekly batch build does not need.

**Stable keys for reports and recommendations,** from OIG's own identifiers. *Why:* a rebuild matches the previous one row by row, which is how every build is reconciled with OIG. *Cost:* a few reports OIG lists twice must be reconciled by hand.

**A containerized API on a local host.** *Why:* no cloud account was needed to start, and the container moves unchanged. *Cost:* availability depends on one machine.

**Hybrid search.** Keyword (BM25) and meaning (vectors) results merged by reciprocal rank fusion. *Why:* people describe problems in their own words, which share few words with OIG's. *Cost:* more reach, not more precision: on identical keywords OIG's own results were more often relevant.

**OIG's text is never rewritten.** Corrections, such as a mistyped station number, are applied as a reviewed list when derived tables are built. *Why:* every answer can be traced to what OIG published. *Cost:* the correction list must be maintained.

---

← [Deployment and operations](../guides/deployment.md) · [Wiki home](../README.md) · [Method](../evaluation/method.md) →
