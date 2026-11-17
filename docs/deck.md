# Deck source: oig-mcp

*Source text for the hackathon presentation deck. Each slide has a title, the body for the slide, a suggested visual, and speaker notes. Slides follow the order of the hackathon's sample deck, with three added: who the server serves (slide 4), the watsonx Orchestrate deployment (slide 9), and the failure analysis (slide 13). Figures come from [evaluation.md](evaluation.md) and [SECURITY.md](../SECURITY.md) as of November 17, 2026. Lines marked UPDATE change after the second Orchestrate round.*

---

## Slide 1: Title

**Title:** VA OIG Oversight Assistant

**Subtitle:** An MCP server that lets any AI agent answer questions across VA Inspector General reports, with a citation for every finding

**Footer:**
- GSA MCP Server and AI Agent Government Hackathon, Dataset Access track
- Troy Sybert, MD
- Deployed on IBM watsonx Orchestrate
- github.com/HacksterT/oig-mcp

**Visual:** None, or the project mark.

**Speaker notes:** The server is the entry. The agents in this deck are the instruments we used to test it.

---

## Slide 2: The challenge

**Title:** The Challenge: A Public Record Built for Reading, Not for Questions

**Body:**

VA's Office of Inspector General (OIG) publishes its oversight work at vaoig.gov: 4,410 reports and 15,649 recommendations, with 11,264 facility responses inside the report PDFs. The record is public, but it is hard to use for the questions oversight work actually asks.

1. **No machine access.** There is no API or bulk export, so no AI assistant can work with the record directly.
2. **Answers are inside documents.** What a facility committed to do, and by when, appears only in report PDFs.
3. **Search finds documents, not patterns.** The site answers "which reports mention this?" It cannot answer "what keeps being cited?", "is this growing year over year?", "how long do fixes like this take?", or "what did other facilities do about it?"
4. **The work falls on people.** Staff preparing for an inspection read prior reports by hand to learn what OIG has found before, at their own facility and at its peers.

**Visual:** A vaoig.gov report page beside a PDF page of facility responses, with the cross-report questions overlaid.

**Speaker notes:** OIG's site is good at finding a document when you know what you want. The gap is any question that spans many documents.

---

## Slide 3: The solution

**Title:** The Solution: An MCP Server Over the Whole OIG Record

**Body:**

oig-mcp gives any MCP-compatible agent seven tools over a structured, regularly refreshed copy of what OIG publishes.

- **Ask in plain language,** across every report, and get exact counts, trends, time to close, recurring findings, and peer commitments.
- **Every finding can be checked.** It comes with the OIG report number, a vaoig.gov link, and the date the data was collected.
- **It states its limits.** It declines what the data cannot support: rating facilities, predicting findings, computing a deadline miss rate, or guessing who was responsible.
- **It runs anywhere MCP does.** The same server is deployed in IBM watsonx Orchestrate and also works with Claude and other MCP clients.

Example questions:
- "Which findings recur across VA medical facilities?"
- "How many suicide prevention findings has OIG made each year since 2020?"
- "What did peer facilities commit to doing when cited for unsecured medication carts?"
- "Prepare a brief for the Durham VA Medical Center's next inspection."

**Visual:** A question going into an agent, the server's tools, and an answer with report numbers and links.

**Speaker notes:** All data is public. The server uses no internal VA systems and no nonpublic information, and it is not an official VA or OIG product.

---

## Slide 4: Who it serves

**Title:** Mission: Oversight That Facilities Can Learn From

**Body:**

| User | What the server gives them |
|---|---|
| **Facility patient safety and quality staff,** preparing for an OIG inspection | The facility's open and repeat findings, the most common findings at peer inspections, and what peers committed to do about them |
| **Program offices** | Whether a finding is isolated or systemic before deciding on a national fix, and how long similar recommendations take to close |
| **Oversight and policy staff** | What is open and aging, by office, topic, or report type, reconciled with OIG's own published counts |

The design favors trust over polish. It produces no facility scores or rankings. A repeat finding means the same issue was cited again, not that nothing was done. A next-inspection date is labeled an estimate, because OIG publishes no schedule.

**Visual:** Three user cards, each with one example question and a cited answer.

**Speaker notes:** This is the service delivery and oversight mission. A facility can learn from how its peers responded instead of starting from nothing.

---

## Slide 5: Server design overview

**Title:** Server Design Overview

**Body:**

The project is built in Python on FastMCP. It has two parts, and the MCP server calls exactly one origin.

- **Data service** (companion repository): crawls vaoig.gov, parses report pages and PDFs into SQLite, and serves a JSON API behind Cloudflare Access with its own API key.
- **oig-mcp** (this repository): 7 tools, 3 resources, and 2 workflow prompts. The data address is set by the operator, never by a tool argument.
  - **Tools:** data status, search, analysis, systemic clusters, one report, a facility profile, an inspection brief.
  - **Resources:** an about page, the facility registry, and filter values.
  - **Prompts:** an inspection readiness checklist and an open-recommendation aging brief.
- **Middleware:** bearer authentication, a per-client rate limit, a usage log, and traces linked to the data service by trace ID.
- **Transports:** stdio (watsonx Orchestrate, desktop clients) and Streamable HTTP (a hosted endpoint for testers and judges).

**Visual:**

```
vaoig.gov ──> data service: crawler, SQLite, JSON API, behind Cloudflare Access
                     │  HTTPS, service token and API key
                     ▼
              oig-mcp: 7 tools · 3 resources · 2 prompts
              auth · rate limit · usage log · traces
                     │  stdio or Streamable HTTP
                     ▼
  watsonx Orchestrate agent · Claude · any MCP client
```

**Speaker notes:** One tool per file, each registering itself. Everything outbound goes through one hardened HTTP client.

---

## Slide 6: Key decision 1

**Title:** Key Decision 1: Tools Built Around the User's Goal, Not the API's Endpoints

**Body:**

**Decision:** Seven tools, each named for a task a user has. Several combine many data requests, so the agent makes one call instead of orchestrating ten.

| Tool | For |
|---|---|
| `vaoig_get_dataset_status` | How current the data is, and the valid filter values |
| `vaoig_search_findings` | Find findings, and what peer facilities committed to do |
| `vaoig_analyze_recommendations` | Exact counts, trends, time to close, aging |
| `vaoig_find_systemic_clusters` | Findings that recur across reports, and how common each is |
| `vaoig_get_report` | One report in full, with each facility response |
| `vaoig_get_facility_profile` | One facility's reports, findings, and repeat findings |
| `vaoig_get_inspection_brief` | Prepare one facility for inspection from the public record |

**Rationale:**
- **Fewer calls means fewer mistakes.** The inspection brief alone runs up to ten searches. A weaker model fails when it must sequence that work itself.
- **Exact answers by design.** Counts come from the analysis tool, never from adding up search results.
- **Precise names.** A shared `vaoig_` prefix and a verb, so the right tool is obvious in any host's tool list.

**Visual:** The inspection brief as one call fanning out to the facility's history, peer findings, and peer commitments.

**Speaker notes:** Routing hints in each description tell a model when to use the tool and when to use another, and tests check that every description says so.

---

## Slide 7: Key decision 2

**Title:** Key Decision 2: Typed, Bounded Contracts in Both Directions

**Body:**

**Decision:** Pydantic models define every input and every result.

- **Inputs:** Enums cover closed sets such as status and grouping. Filters reject unknown fields rather than dropping them, because a dropped filter would silently return numbers for a wider set than asked. Every list, string, and offset is bounded.
- **Outputs:** Every tool declares an output schema, so clients see the shape of a result in the tool list and can check each one.
- **Errors the agent can act on:** A failure comes back as an MCP error result with a hint chosen by cause: a rejected filter, a busy search queue, a slow search, a data service failure, or an unreachable service. "Not found" and "several facilities match" are answers, not errors.
- **Mistakes corrected at the boundary:** An office name put in the wrong filter is refused with the fix ("Use action_office='VBA' instead"). An empty result says to check the filter values before concluding there is nothing.

**Visual:** One tool's input schema beside its output schema, with an error result and its hint.

**Speaker notes:** The last point came from evaluation. The Orchestrate agent wrote an office's full name in the domain filter, matched nothing, and told the user there was no data. The server now catches that.

---

## Slide 8: Key decision 3

**Title:** Key Decision 3: Trust Carried in Every Answer, by the Server

**Body:**

**Decision:** Guardrails live in the server's instructions and results, not in one host's system prompt, so they hold for every agent that connects.

- **Provenance on every result:** the data date, whether it is stale, and a report number and vaoig.gov link on every record.
- **Notices the agent passes on:** caveats the data requires, such as why OIG's dashboard shows 586 open recommendations against this data's 567.
- **Scope stated by the server:** no medical, benefits, or legal advice; emergencies sent to 911; no facility rankings or forecasts; never a guess about who was responsible.
- **Report text treated as a quotation:** results name the fields that quote OIG reports and say to cite them, never to follow instructions in them. Every tool is read-only.

**Visual:** A result with its provenance block, notices, and quoted fields highlighted.

**Speaker notes:** This is why the Orchestrate agent needs only one instruction: answer only from what the tools return.

---

## Slide 9: Running on IBM watsonx Orchestrate

**Title:** Deployed on IBM watsonx Orchestrate

**Body:**

- **Local toolkit:** Orchestrate runs the server over stdio inside its own runtime, so the server has no network endpoint of its own there.
- **Credentials from a connection:** the data service address and credentials come from a key_value connection, never from code or the repository.
- **A minimal agent:** it uses the seven tools, runs GPT-OSS 120B, and has one instruction: "Answer only from what the OIG tools return. Do not use general knowledge or information outside the tool results."
- **Evaluated in place:** IBM's Agent Development Kit ran the same gold questions against the deployed agent, three times.
- **Traced end to end:** every request the server makes carries a trace ID to the data service, so each Orchestrate conversation can be checked against the requests behind it.

**Visual:** A screenshot of the Orchestrate agent answering with cited reports, and the toolkit's seven tools.

**Speaker notes:** The same server runs over Streamable HTTP with bearer authentication for other hosts. No code differs between the two deployments.

---

## Slide 10: Demo

**Title:** MCP Server Demo

**Body:** A short screen recording embedded in the slide, as the sample deck does, with screenshots as a fallback. Suggested flow:

1. "How current is the data?" Dataset status, with the data date and its reconciliation with OIG's own counts.
2. "Which offices have the most recommendations open longer than a year?" An exact table from the analysis tool.
3. "What did facilities commit to doing about unsecured medication carts?" Search, with peer commitments and report links.
4. "Prepare an inspection brief for a named facility." The inspection brief.
5. "Which facility is the worst?" A declined request, with what the server can offer instead.

**Visual:** Screenshots from the Orchestrate agent, or from Claude, for each step.

**Speaker notes:** End on the refusal. Knowing what not to answer is part of the design.

---

## Slide 11: Evaluation setup

**Title:** MCP Server Evaluation: Setup

**Body:**

**Framework:** Arize Phoenix for the harness, traces, and experiments, plus IBM's Agent Development Kit for the deployed Orchestrate agent.

**Gold dataset:** 24 questions and 6 adversarial questions. The answers are computed by SQL from a frozen data snapshot, not from the API under test. The harness refuses to run if the server's data differs from the snapshot.

| Kind | Questions |
|---|---|
| Exact figures | 14 |
| Lists | 2 |
| Search | 2 |
| Workflow | 1 |
| Behavior: an ambiguous name, an unanswerable question, requests to rank, predict, or compute a miss rate | 5 |
| Adversarial: instruction override, injected text, a nonexistent report, a medical emergency, naming staff, out of domain | 6 |

**The agent gets no project prompt.** Its system prompt is the server's own instructions, as any MCP host receives them.

**Scoring:**
- **By code, where it can:** exact facts, tool choice, citation and data date, and whether every cited report exists.
- **By two judges from different model families,** where code cannot: Claude Opus 5.5 and Llama 3.3 70B on IBM watsonx.ai.

**Baselines and models:**
- The same questions with no server.
- Five agent models: Claude Opus 5.5 and Sonnet 5.5, Llama 3.3 70B, GPT-OSS 120B in Orchestrate, and DeepSeek V4 Pro.

**Visual:** A pipeline from the gold set (built by SQL) to the agent with only the server's tools, then code checks, two judges, and results in Phoenix.

**Speaker notes:** The weaker models are deliberate. A strong model shows what the server makes possible, and a weaker one shows where the server must carry more of the load.

---

## Slide 12: Evaluation results

**Title:** MCP Server Evaluation: Results

**Body:**

**What the server adds** (questions passing every check):

| Model | No tools | With the server |
|---|---|---|
| Claude Opus 5.5 | 3 of 24 (1 of 16 exact facts) | 23 of 24 (16 of 16) |
| Llama 3.3 70B, watsonx.ai | 2 of 24 (0 of 16) | 9 of 24 (11 of 16) |

**Across platforms:**
- **Claude Opus 5.5:** 23 of 24 on every run from November 4 to 17, and 22 of 24 after the result-size changes, where the new miss was "agreed" for "concur" on a correct answer. Claude Sonnet 5.5 scored 23 of 24.
- **GPT-OSS 120B, the Orchestrate agent, three runs:** 10, 8, and 11 of 24 on this project's scoring; IBM's engine scored 14, 14, and 13. UPDATE after the second round.
- **Citations:** no answer from the server-backed Claude, Llama, or Orchestrate runs cited a report that does not exist.
- **Judge agreement:** the two judges agreed on 89 of 90 harness answers.

**Operations:**
- **Per question, Claude Opus 5.5:** about 14 seconds on average, with 2.3 tool calls, about 25,000 input tokens, and 1,400 output tokens. Tool results make up most of the input.
- **Latency:** median tool latency from about 0.13 seconds (analysis) to about 2 seconds (the inspection brief).
- **Reliability:** every Orchestrate call that reached the data service succeeded.
- **Cost:** about $3 per full Claude Opus 5.5 run, including the judge.

**Limits:** One builder wrote the questions and the server, and fixes followed failures on these same questions. Twenty-four questions are a check, not a statistical estimate. The service has not been load tested.

**Visual:** A screenshot of the Phoenix experiments chart for the 24-question dataset, showing score and average latency across runs, as the sample deck does. Beside it, a bar chart of no tools against with the server for both models.

**Speaker notes:** The one Opus failure is the Durham list question. It listed all eight inspection reports correctly, but it also named the excluded reports under a "left out" heading, and the scorer counted those as extras. The scorer was not changed after seeing the result, so it stays a failure.

---

## Slide 13: Failure analysis

**Title:** Every Failure Traced to Its Cause, Then Fixed and Retested

**Body:**

Each failure was read against the tool results and the data service's request traces, then sorted by cause.

| Cause | Example | Response |
|---|---|---|
| Server | An office name in the wrong filter matched nothing, and the agent said there was no data | Fixed in the server |
| Data service | Counting with a response filter failed | Fixed in the data service |
| Model | Report numbers given without links | Citation requested in every result |
| Platform | Expired logins in Orchestrate | Operational: log in fresh before each run |
| Scorer | Report numbers with non-breaking hyphens were missed | Scorer fixed, every run rescored |

**Retested with the same model, only the server changed:**
- **Adversarial set:** Claude Opus 5.5 went from 5 to 6 of 6, Llama 3.3 70B from 0 to 4 of 6.
- **Llama 3.3 70B on the 24 questions:**
  - right tool: 17 of 20 to 19 of 20
  - citation: 1 of 8 to 3 of 8
  - data date: 1 of 5 to 3 of 5
- **Claude Opus 5.5 regression checks:** 23 of 24 after the scope changes, every measure unchanged; 22 of 24 after the result-size changes, with the judge agreeing on all 24.

**Visual:** The cause table, with before-and-after bars.

**Speaker notes:** The traces settled who was at fault. The first report blamed the server for Orchestrate's own connection errors, and the traces showed every server call had succeeded. These retests are not blind: the adversarial questions and the fixes were written the same night.

---

## Slide 14: Security considerations

**Title:** Security Considerations

**Body:**

**Public data, handled with care.** All data is OIG's published record, with no CUI. Inspection findings are addressed to roles and offices. The server never guesses who was responsible and names a person only where a quoted finding does.

| Surface | Mitigation | Checked by |
|---|---|---|
| MCP endpoint | A bearer token compared in constant time; a per-client rate limit; Host and Origin checks for local HTTP | 22 deployment checks |
| Tool input | Typed and bounded; path traversal, injection, and search syntax refused cleanly | 48 robustness checks |
| Outbound requests | One fixed origin, no redirects or proxies, bounded responses, at most eight requests at once | Automated tests |
| Prompt injection | Report text marked as quotation; read-only tools; scope in the server's instructions | 6 adversarial questions |
| Secrets | From the environment or an Orchestrate connection; never in results, logs, or the image | 15 image checks, history scan |
| Container and supply chain | Non-root, no capabilities, read-only filesystem; locked dependencies audited on every change; pinned image and CI actions | CI, Dependabot |

**Independent review (November 17):** a separate review agent found no high-severity issues. Its medium and low findings are fixed, each with a test.

**Visual:** The table, or the attack surface as a diagram with each mitigation marked.

**Speaker notes:** Questions sent during the hackathon are recorded in traces so the builder can see how the server is used. Users are told so and asked not to enter patient or nonpublic information.

---

## Slide 15: Lessons learned and recommendations

**Title:** Lessons Learned and Recommendations

**Body:**

1. **Compute gold answers from the source data, not from the API under test.** A gold set built through the API would repeat its errors. SQL against a frozen snapshot caught them.

2. **Run a no-tool baseline and a weaker model.** The baseline turns "the server helps" into a measured difference. The weaker model shows what the server must make explicit, such as which tool counts and which one searches.

3. **Make an empty result say so.** A filter that silently matches nothing becomes a confident wrong answer. Tell the agent to check its filter values before concluding there is no data.

4. **Put scope and guardrails in the server, not in one host's prompt.** The server's instructions and results carry citations, caveats, and refusals to every agent that connects, including one with a single instruction.

5. **Read failures against request traces before assigning fault.** Trace IDs that link each tool call to the data requests behind it separated server, model, platform, and scorer failures.

**Visual:** None, or one icon per lesson.

**Speaker notes:** The full record, entry by entry, is in docs/lessons-learned.md.
