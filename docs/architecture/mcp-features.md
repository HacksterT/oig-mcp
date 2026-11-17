[Wiki](../README.md) › Architecture › MCP features

# MCP features

*The MCP protocol features the server uses beyond plain tool calls, how each works, and which hosts support them.*

## Elicitation

**What it is.** Elicitation lets a server pause a tool call and ask the user a question directly, through the host. The server sends a message and a small schema for the answer; the host shows it, usually as a form; the user accepts with an answer, declines, or cancels; and the answer goes straight back to the server, which checks it and finishes the same call. The model is not in the loop, so the user's choice reaches the server unchanged.

**How the server uses it.** When a facility name matches several facilities, such as "Columbia VA" (South Carolina, Missouri, and the District of Columbia) or "Tennessee VA" (Memphis, Mountain Home, and Tennessee Valley), the server asks which one is meant, as a single choice listing each match by name and station number. It accepts only one of the matching stations; any other answer, a malformed one, a decline, or no answer within two minutes returns the matches instead. A host that declares URL mode only, which cannot show a form, is never asked. When the user chooses, the result opens with a notice that the user chose this facility from the matches and that the answer covers it alone: the model never sees the form, so without the notice it reads one profile as the server's guess, and in testing it second-guessed the user or looked up the others anyway.

**Two protocol paths.** On protocol 2026-07-28 the tool returns an `input_required` result carrying the question, and the client calls again with the answer, so each round is a self-contained request. On 2025-11-25 and earlier the server asks within the call, over the open connection. Over stdio both always work. Over HTTP the hosted endpoint keeps a session per client and streams its replies, so it can ask on every protocol version.

**The fallback is the main path in practice.** A host that cannot show a form gets the list of matches with a `next_step`: do not choose one for the user, not even the largest or best known, because findings from the wrong facility would be credited to the one they meant; list them, ask, and call again with the station number. State-filtered analyses and searches likewise name the facilities they pool, and say to ask if the user meant one VA.

**Host support** (checked in each host's installed code, November 17, 2026):

| Host | Declares | Shows the server's form? | Observed with this server |
|---|---|---|---|
| MCP Python SDK client | Form | Yes | The tests and the robustness check: asked, answered, and invalid or malformed answers ignored, on both protocol versions over HTTP; a URL-only declaration is never asked |
| VS Code 1.145 (Copilot chat) | Form and URL | Expected, over stdio or HTTP | Not yet tried |
| Cursor 3.26 | Form | Expected, over stdio or HTTP | Not yet tried |
| Claude Code 2.1 | Form | Yes, over stdio | "Columbia VA": the form listed three facilities and the answer covered the one chosen. Before the choice notice, the model doubted the choice or looked up the others too; after it, one call instead of three or four ([the three takes](../evaluation/results.md#the-form-in-claude-code)) |
| Grok (xAI) | Form and URL | Expected | Grok Bot over HTTP: the matches and the next step; its form not yet seen |
| Claude Desktop 5.11 | URL only | No | The matches; after the next step was added, it asked in chat |
| Hermes Agent | Approve or deny only | No | Before the next step, it chose a facility; after, it offered the matches with its own `clarify` tool |
| watsonx Orchestrate | None observed | No | "New York VA": listed the matches and asked |

Hosts interpret this feature differently, and that is a finding, not a defect: the same server result became a form, a list of choices, or a plain question, and with the next step in place no host chose a facility for the user.

## Argument completions

Hosts that show completions suggest values as a person types: the facility for the inspection checklist prompt, as "Name (station)" from the facility registry; the topic for the aging brief prompt; and the facet for `vaoig://taxonomy/{facet}`. Completion is a convenience: a failure yields no suggestions, never an error, and no tool depends on it.

## Output schemas

Every tool declares its result shape as a JSON schema built from Pydantic models, so a host sees what a tool returns before calling it and can check every result against it.

## Provenance, notices, and citations

Every data result carries a `provenance` block (the data date, whether it is stale, how to cite it, and which fields quote report text) and a `notices` list of text the assistant must pass on. Every record with a report number and link carries a ready-made `citation`, so a model can copy a report number and link together rather than assemble them.

## Resources and prompts

Three resources give scope and reference data a host can read without a tool call: `vaoig://about` (scope and citation rules), `vaoig://facilities` (the facility registry), and `vaoig://taxonomy/{facet}` (OIG's filter values). Two prompts package common workflows: `inspection_readiness_checklist` and `open_recommendation_aging_brief`.

## Annotations

Every tool is annotated read-only, non-destructive, and idempotent, so a host can run it without asking for approval to change anything.

---

← [Server design](../architecture/server-design.md) · [Wiki home](../README.md) · [Connecting](../guides/connecting.md) →
