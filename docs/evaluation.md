# Evaluation

*GSA MCP and AI Agent Hackathon. This document follows the structure of the hackathon's sample evaluation document. The full method is in [testing-architecture.md](testing-architecture.md), every score with its limits in [testing-results.md](testing-results.md), and what each test taught in [lessons-learned.md](lessons-learned.md).*

| | |
|---|---|
| **Server under test** | oig-mcp, an MCP server over VA Office of Inspector General (OIG) reports and recommendations, with seven tools |
| **Evaluation frameworks** | Arize Phoenix (harness, traces, experiments); IBM's Agent Development Kit (`orchestrate evaluations evaluate`) against the server deployed in IBM watsonx Orchestrate |
| **Agent models** | Claude Opus 5.5 and Claude Sonnet 5.5 (Anthropic API); Llama 3.3 70B (IBM watsonx.ai, temperature 0); GPT-OSS 120B (the Orchestrate agent); DeepSeek V4 Pro 0813 (Hermes Agent) |
| **Judges** | Code checks; Claude Opus 5.5; Llama 3.3 70B on watsonx.ai; IBM's evaluation engine (GPT-OSS 120B) |
| **Datasets** | 24 gold questions, plus 6 adversarial questions, with answers computed by SQL from a frozen data snapshot (`2bb10bd321e08dfc`, data as of November 4, 2026) |
| **Dates** | November 4 to 17, 2026 |

## 1. Overview and objectives

The goal is to show whether the server lets an agent that knows nothing else answer real oversight questions correctly, cite the OIG report behind each finding, and stay within what the data supports. The server is the subject of every test. The models are instruments: a strong model shows what the server makes possible, and a weaker one shows where the server must carry more of the load. A failure is traced to its cause (the server, the model, or the test) and fixed in the server where the server is at fault.

A passing answer gives the exact figure the data holds, uses the right tool, cites each report by number and link where a report is the source, states the data date where currency matters, and declines what the data cannot support: ranking facilities, predicting findings, computing a deadline miss rate, or naming individuals.

The seven tools are built around what a user is trying to do, not around the data API's endpoints. Several combine many API calls: the inspection brief, for example, assembles a facility's open findings, its repeat findings, the most common findings across peer inspections, and what peers committed to do about them.

| Tool | What it is for |
|---|---|
| `vaoig_get_dataset_status` | How current the data is, and the valid filter values |
| `vaoig_search_findings` | Find findings, and what peer facilities committed to do |
| `vaoig_analyze_recommendations` | Exact counts, trends, time to close, not-implemented rates, open-item aging |
| `vaoig_find_systemic_clusters` | Findings that recur across reports, and how common each is |
| `vaoig_get_report` | One report in full, with each facility response |
| `vaoig_get_facility_profile` | One facility's reports, inspections, findings, and repeat findings |
| `vaoig_get_inspection_brief` | Prepare one facility for an inspection from the public record |

## 2. Testing methodology

### Layers

| Layer | What it checks |
|---|---|
| Automated tests | 238 tests on every change: each tool's inputs, results, output schema, error messages and hints, authentication, and that each description tells a model when to use the tool |
| Image checks | 15 checks on the container: no secret inside, a non-root user, refusal to start without a valid token or with a plain-HTTP data address |
| Deployment checks | 22 checks on a running server: seven kinds of bad credentials refused, all seven tools listed, live data with no secret in it |
| Robustness check | 46 checks on a running server: hostile and malformed input to every tool and to argument completion, a burst past the rate limit, searches past the data API's capacity, and no internal detail in any reply |
| Agent evaluation | Gold questions answered by an agent that has only the server's tools, scored by code and judges |
| Baseline | The same questions and models with no server |
| Cross-platform runs | The same questions on other models and hosts, including IBM's own agent, three runs |

### Framework and reproducibility

The harness ([`eval/phoenix/`](../eval/phoenix/)) gives the agent no project-specific prompt: its system prompt is the server's own `instructions`, as any MCP host receives them, and it connects over authenticated HTTP. Every run is recorded in Arize Phoenix with each tool call, its arguments, and its latency, and kept in [`eval/results/`](../eval/results/). The data is frozen, and the harness refuses to run if the server's data differs from the pinned snapshot. One command runs a set:

```bash
uv run --group eval python eval/phoenix/run_experiment.py --model claude-opus-5-5
uv run --group eval python eval/phoenix/run_experiment.py --model meta-llama/llama-3-3-70b-instruct
uv run --group eval python eval/phoenix/run_experiment.py --no-tools          # baseline
uv run --group eval python eval/phoenix/run_experiment.py --gold adversarial  # adversarial set
```

In watsonx Orchestrate, the server runs as a local toolkit over stdio. The agent has the seven tools and one instruction: "Answer only from what the OIG tools return. Do not use general knowledge or information outside the tool results." IBM's Agent Development Kit runs test files generated from the same gold set ([`eval/orchestrate/tests/`](../eval/orchestrate/tests/)).

### Golden dataset

The gold answers do not come from the API being tested: [`build_gold.py`](../eval/gold/build_gold.py) computes them by SQL against the frozen snapshot, opened read-only. The questions span the kinds of work an oversight analyst does:

| Kind | Questions | Examples |
|---|---|---|
| Exact | 14 | Open recommendations now; median days to close for one office; one facility's oldest open item |
| List | 2 | Top offices by open items; every inspection report for one facility |
| Search | 2 | A plain-language question; what facilities committed to do about a finding |
| Workflow | 1 | Preparing a facility for inspection |
| Behavior | 5 | An ambiguous facility name; an unanswerable question; requests to rank facilities, predict findings, or compute a deadline miss rate |
| Adversarial | 6 | An instruction to ignore the rules; an instruction injected into pasted text; a report that does not exist; a medical emergency; a request to name employees; an out-of-domain question |

### Evaluators

Code scores everything it can, so those scores repeat exactly: exact facts, list recall and precision, tool choice, whether a report number and link are given, whether the data date is stated, and whether every cited report number and link exists among the snapshot's 4,415 reports. An AI judge decides only what code cannot: whether the answer agrees with the gold reference, and whether it meets each written behavior criterion. Every answer set is judged twice, by Claude Opus 5.5 and by Llama 3.3 70B on IBM watsonx.ai, with the same prompt. Orchestrate runs are also read by IBM's own evaluation engine and checked against the data API's request traces, so each result has three independent readings.

### Test design rationale

The questions target the failures that matter for an oversight tool: a wrong number, a citation to a report that does not exist, an answer that goes beyond the data (a rating, a forecast, a rate the data cannot support), and an answer to a question the server has no authority to answer. A no-tool baseline measures what the server adds. Several models of different strength measure how much of the work the server itself does. Three runs on Orchestrate separate consistent failures from chance.

## 3. Performance metrics

### Metrics tracked

Questions passing every check; exact facts present; agreement with the gold reference; tool selection; behaviors and caveats; citation integrity; citation and data date where required; consistency across runs; judge agreement; tool latency, errors, and cost.

### What the server adds

| Model | No tools | With the server |
|---|---|---|
| Claude Opus 5.5 | 3 of 24 (1 of 16 exact facts) | 23 of 24 (16 of 16) |
| Llama 3.3 70B, watsonx.ai | 2 of 24 (0 of 16) | 9 of 24 (11 of 16) |

Without the server, neither model could give the data's figures, beyond one by Opus; the few questions they passed were refusals, which need no data. With it, Claude Opus 5.5 gives every exact figure, and has matched that result on every rerun since November 4.

### Results across platforms

| Platform | Questions passing every check | Notes |
|---|---|---|
| Claude Opus 5.5, harness | 23 of 24, on every run from November 4 to 17 | The one failure is a scoring call on a correct answer, kept as a failure |
| Claude Sonnet 5.5, harness | 23 of 24 | |
| Llama 3.3 70B, harness on watsonx.ai | 9 of 24, before and after the November 17 server changes | Tool choice, citations, and data dates improved; one question overflows the model's context |
| GPT-OSS 120B, the Orchestrate agent, three runs | 10, 8, and 11 of 24 on the project's scoring; IBM's engine: 14, 14, and 13 | Server changes from these runs are deployed; a second round, with the adversarial questions, is planned for November 17 |
| DeepSeek V4 Pro, Hermes Agent | All 18 answers agree with the gold reference | Not a blind run |

**Citation integrity.** No answer from the server-backed Claude, Llama, or Orchestrate runs cited a report number that does not exist. The only one on any platform is in a logged answer from the Hermes agent.

**Consistency.** Claude Opus 5.5 scored the same on every rerun. On Orchestrate, 5 questions passed all three runs, 9 failed all three, and 10 varied, which is why each question runs three times.

**Judge agreement.** On the harness answer sets, the Claude and watsonx.ai judges gave the same pass or fail on 89 of 90 answers; on the Orchestrate runs, 67 of 71. IBM's engine agreed with the project's scoring on 52 of 72: it scores the whole conversation and has no citation or data-date check, so it passed 16 answers the project failed.

### Failure analysis

Each failure was read against the tool results and the data API's traces and sorted by cause.

| Cause | Examples | Response |
|---|---|---|
| Server | An office written as its full name, or put in the wrong filter, matched nothing and the agent said there was no data; facility counts routed to search; a data API error described as "not reachable"; out-of-scope questions not covered by the server's instructions | Fixed in the server and verified (see below) |
| Data service | Counting with only a facility-response or domain filter failed | Fixed in the data API; the failing requests now succeed |
| Model | A misread 31-row table; skipped program filter; report numbers given without links | The server now precomputes the peak year and states the program filter in the tool description; citation is requested in every result, and gaps that remain are reported |
| Platform | Two expired-login errors and one internal connection failure in Orchestrate; one dropped connection | Operational: log in fresh before each run |
| Scorer | Report numbers written with non-breaking hyphens were not recognized | Scorer fixed; every earlier run rescored with no change |

### Server changes verified by retesting

| Test | Before | After |
|---|---|---|
| Adversarial set, Claude Opus 5.5 | 5 of 6 | 6 of 6 |
| Adversarial set, Llama 3.3 70B | 0 of 6 | 4 of 6 |
| 24 questions, Llama 3.3 70B: passing every check | 9 of 24 | 9 of 24 |
| 24 questions, Llama 3.3 70B: right tool, citation, data date | 17 of 20, 1 of 8, 1 of 5 | 19 of 20, 3 of 8, 3 of 5 |
| 24 questions, Claude Opus 5.5 (regression check) | 23 of 24 | 23 of 24, every measure unchanged |

The model and its settings were the same before and after; only the server changed. On the 24 questions, Llama's total did not move: two questions it had failed now pass, two it had passed now fail, and the Durham question still overflows its 128K-token context, an open item. These retests are not blind: the adversarial questions and the fixes were written the same night.

### Operational metrics

Measured through the server against the hosted data API: median tool latency from about 0.13 seconds (analysis) to about 2 seconds (the inspection brief, which runs up to ten searches). In Orchestrate the agent's average response time was 5.9 to 7.6 seconds per turn, most of it the model. Of 72 Orchestrate conversations, 4 met a platform error; every call that reached the data API succeeded. A full Claude Opus 5.5 run of 24 questions costs about $3 at list prices, including the judge.

### Error handling

Every tool reports a failure as an MCP error result with a hint the agent can act on, distinguished by cause: a rejected filter, a busy search queue, a slow search, a data API failure, or an unreachable API. A filter value the data does not use is refused with the fix where it can be (an office in the domain filter names the office filter), and an empty result says to check the filter values before concluding there is nothing. "Not found" and "several facilities match" are answers, not errors. Each behavior is covered by automated tests.

## 4. Security considerations

The full design, every check with its latest result, the November 17 review, and the accepted risks are in [SECURITY.md](../SECURITY.md).

**Data classification.** The data is public: OIG's published reports and recommendations at vaoig.gov, with no CUI. Inspection findings are addressed to roles and offices; 77 of 15,649 recommendations, mostly from administrative investigations, name an official as OIG published them. The server never guesses who was responsible and names a person only where a quoted finding does. Questions sent during the hackathon are recorded in traces, users are told so, and they are asked not to enter patient or nonpublic information.

**Scope containment.** Five behavior questions and six adversarial questions test that the agent declines what the data cannot support, refuses to rank facilities or guess who was responsible, gives no medical advice and sends an emergency to 911, and does not invent a report. The server states its scope in its own instructions, so the guardrail holds for any host, not only one configured agent.

**Untrusted input and prompt injection.** Report text is quoted from OIG reports. Every result marks the fields that quote report text and says to cite them and never follow instructions in them, and every tool is read-only. The adversarial set includes an instruction injected into text a user pastes; both models ignored it after the server changes. Tool arguments are typed and bounded, and a robustness check sends every tool path traversal, header and query injection, SQL and search syntax, and values past every bound: all 46 checks pass, with no stack trace, upstream address, or credential in any reply.

**Secrets and configuration.** Credentials load from the environment, or in Orchestrate from a key_value connection, and are never committed: a scan of the repository's full history found none. The server refuses to start without a bearer token of at least 32 characters, or with a plain-HTTP remote data address. No secret appears in tool results, logs, or the image, checked by the image and deployment checks.

**Transport and isolation.** Over HTTP, every request needs the bearer token, compared in constant time; seven kinds of bad credentials are refused. The data API sits behind Cloudflare Access and requires both its service token and an API key. The server calls one fixed origin, with no redirects or proxies, bounded responses, and at most eight upstream requests at once. Local HTTP binds to 127.0.0.1 and checks Host and Origin headers. The container runs as a non-root user with no Linux capabilities and a read-only filesystem. In Orchestrate, the server runs over stdio inside Orchestrate's runtime, with no network endpoint of its own.

**Supply chain.** Dependencies are locked with hashes and audited for known vulnerabilities on every change; none are known. The base image is pinned by digest and CI's actions by commit. Dependabot has raised 16 alerts since the repository opened, all fixed.

**Independent review.** A separate review agent read the code and probed the running server on November 17. It found no high-severity issues. Its two medium findings (oversized arguments could flush the traces, and upstream fan-out was unbounded) and its low findings are fixed, each with a test; two accepted risks are documented.

## 5. Lessons learned and recommendations

### What worked

Gold answers computed independently of the API caught errors the API would have repeated. Scoring facts and citations by code made results repeatable, and two judges from different model families, with IBM's engine and the data API's traces as further readings, showed when a single judge was wrong. Testing with weaker models showed what the server must make explicit, and each fix was verified by rerunning the same model. The no-tool baseline turned "the server helps" into a measured difference.

### Limitations

One builder wrote the questions and the server, and some fixes followed failures on these same questions, so later runs are not blind on those points. 24 questions, with 6 adversarial, are a check, not a statistical estimate. Judges are models, and no person reviewed every answer. The service has not been load tested.

### Recommendations

- Compute gold answers from the source data, not from the API under test.
- Run a no-tool baseline and a weaker model: the baseline shows what the server adds, and the weaker model shows what it must make explicit.
- Make an empty result say so: a filter that silently matches nothing becomes a wrong answer.
- Put scope and guardrails in the server's own instructions and results, not in one host's prompt.
- Read failures against the server's request traces before deciding who is at fault.
- Use two judges from different model families, and review the answers where they disagree.

The full record, entry by entry, is in [lessons-learned.md](lessons-learned.md).
