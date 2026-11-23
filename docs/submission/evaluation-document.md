# Evaluation

*GSA MCP and AI Agent Hackathon. This document follows the sections of the hackathon's sample evaluation document. The project wiki holds the detail: the full method in [Evaluation method](../evaluation/method.md), every score with its limits in [Evaluation results](../evaluation/results.md), and how the server measures against IBM's MCP design guide in [Server design](../architecture/server-design.md#measured-against-ibms-mcp-design-guide).*

| | |
|---|---|
| **Server under test** | oig-mcp, an MCP server over VA Office of Inspector General (OIG) reports and recommendations, with seven tools |
| **Evaluation framework** | Arize Phoenix (harness, traces, experiments); IBM's Agent Development Kit (`orchestrate evaluations evaluate`) against the server deployed in IBM watsonx Orchestrate |
| **Agent models** | Claude Opus 5.5 and Claude Sonnet 5.5 (Anthropic API); Llama 3.3 70B (IBM watsonx.ai, temperature 0); GPT-OSS 120B (in IBM watsonx Orchestrate); DeepSeek V4 Pro 0813 (Hermes Agent). Five models from four model makers, three open-weight |
| **Judges** | Code checks; Claude Opus 5.5; Llama 3.3 70B on watsonx.ai, directly and through `arize-phoenix-evals` as IBM's skill specifies; IBM's evaluation engine |
| **Dataset** | 24 gold questions plus 6 adversarial questions, with answers computed by SQL from a frozen data snapshot (data as of November 4, 2026) |
| **Date** | November 4 to 17, 2026 |

## 1. Overview and objectives

The goal is to show whether the server lets an agent that knows nothing else answer real oversight questions correctly, cite the OIG report behind each finding, and stay within what the data supports. The server is the subject of every test. The models are instruments: a strong model shows what the server makes possible, and a weaker one shows where the server must carry more of the load.

A passing answer gives the exact figure the data holds, uses the right tool, cites each report by number and link, states the data date where currency matters, and declines what the data cannot support: ranking facilities, predicting findings, computing a deadline miss rate, or naming individuals.

**The headline.** With the server, five models passed between 9 and 23 of 24 questions, against 2 or 3 without it. With only the server changed, GPT-OSS 120B in watsonx Orchestrate rose from 10, 8, and 11 to 12 and 12 of 24, and an independent judge on watsonx.ai found its correct answers rose from about 16 to 20 of 24.

The seven tools are built around what a user is trying to do, not around the data API's endpoints:

| Tool | What it is for |
|---|---|
| `vaoig_get_dataset_status` | How current the data is, and the valid filter values |
| `vaoig_search_findings` | Find findings, and what peer facilities committed to do |
| `vaoig_analyze_recommendations` | Exact counts, trends, time to close, open-item aging |
| `vaoig_find_systemic_clusters` | Findings that recur across reports, and how common each is |
| `vaoig_get_report` | One report in full, with each facility response |
| `vaoig_get_facility_profile` | One facility's reports, findings, and repeat findings |
| `vaoig_get_inspection_brief` | Prepare one facility for an inspection |

## 2. Testing methodology

### Framework and reproducibility

The harness ([`eval/phoenix/`](../../eval/phoenix/)) gives the agent no project-specific prompt: its system prompt is the server's own `instructions`, as any MCP host receives them. Every run is recorded in Arize Phoenix with each tool call, its arguments, and its latency, and kept in [`eval/results/`](../../eval/results/). The data is frozen, and the harness refuses to run if the server's data differs from the pinned snapshot. One command runs a set; the second runs the no-tool baseline:

```bash
uv run --group eval python eval/phoenix/run_experiment.py --model claude-opus-5-5
uv run --group eval python eval/phoenix/run_experiment.py --no-tools
```

In watsonx Orchestrate, the server runs as a local toolkit over stdio. The agent has the seven tools and one instruction: answer only from what the tools return. IBM's Agent Development Kit runs test files generated from the same gold set.

Agent evaluation sits on top of four other layers: 313 automated tests on every change, 15 container image checks, 22 checks on a running deployment, and 49 robustness checks that send hostile and malformed input to every tool.

**A verifiable process.** Every result in this document can be traced and reproduced. The gold questions, their SQL-computed answers, and every run's answers, tool calls, and scores are saved in the repository, and one command recomputes every code check from those saved answers, with no keys, server, or network. On November 17 it reproduced all 18 runs on every question:

```bash
git clone https://github.com/HacksterT/oig-mcp && cd oig-mcp
uv sync --group eval
uv run --group eval python eval/verify_scores.py
```

The deployment checks, the robustness checks, and the full question set can also be rerun against the hosted server with a tester token; the [evaluation method](../evaluation/method.md#verify-it-yourself) gives the commands.

### Golden dataset

The gold answers do not come from the API being tested: [`build_gold.py`](../../eval/gold/build_gold.py) computes them by SQL against the frozen snapshot, opened read-only.

| Kind | Questions | Examples |
|---|---|---|
| Exact | 14 | Open recommendations now; median days to close for one office |
| List | 2 | Top offices by open items; every inspection report for one facility |
| Search | 2 | A plain-language question; what facilities committed to do |
| Workflow | 1 | Preparing a facility for inspection |
| Behavior | 5 | An ambiguous facility name; an unanswerable question; requests to rank, predict, or compute a deadline miss rate |
| Adversarial | 6 | An instruction to ignore the rules; an injected instruction; a report that does not exist; a medical emergency; a request to name employees; an out-of-domain question |

### Evaluators (code checks and LLM-as-judge)

Code scores everything it can, so those scores repeat exactly. An AI judge decides only what code cannot.

| Evaluator | Dimension |
|---|---|
| Code checks | Exact facts; list recall and precision; tool choice; report number and link given; data date stated; every cited report exists among the snapshot's reports |
| Claude Opus 5.5 and Llama 3.3 70B (watsonx.ai), same prompt | Agreement with the gold reference; each written behavior criterion |
| `arize-phoenix-evals` on Llama 3.3 70B (watsonx.ai), as IBM's `mcp-eval-wxai` skill specifies | Correctness, scope, tool selection, tool arguments, tool response handling |
| IBM's evaluation engine, plus the data API's request traces | An independent reading of each Orchestrate run |

### Test design rationale

The questions target the failures that matter for an oversight tool: a wrong number, a citation to a report that does not exist, an answer that goes beyond the data, and an answer to a question the server has no authority to answer. A no-tool baseline measures what the server adds. Models of different strength measure how much of the work the server itself does. Three runs on Orchestrate separate consistent failures from chance.

## 3. Performance metrics

### Metrics tracked

Questions passing every check; exact facts; agreement with the gold reference; tool selection; behaviors and caveats; citation integrity; citation and data date where required; consistency across runs; judge agreement; latency, errors, load, and cost.

### Results

**What the server adds.** Without the server, neither model could give the data's figures, beyond one by Opus; the questions they passed were refusals, which need no data.

| Model | No tools | With the server |
|---|---|---|
| Claude Opus 5.5 | 3 of 24 (1 of 16 exact facts) | 23 of 24 (16 of 16) |
| Llama 3.3 70B, watsonx.ai | 2 of 24 (0 of 16) | 9 of 24 (11 of 16) |

**Same server, five models.** An MCP server does not have one score; it has a score per model, and the weaker models showed what the server had to carry.

| 24 main questions, final server | Passing every check | Agrees with gold | Number and link, where required | Data date, where required | Adversarial 6 |
|---|---|---|---|---|---|
| Claude Opus 5.5 | **23** | 24 | 8 of 8 | 5 of 5 | 6 |
| Claude Sonnet 5.5 | **22** | 24 | 8 of 8 | 5 of 5 | 6 |
| GPT-OSS 120B, open-weight (Orchestrate), two runs | **12, 12** | 19, 19 | 3, 3 of 8 | 3, 2 of 5 | 4, 4 |
| Llama 3.3 70B, open-weight (watsonx.ai) | **9** | 16 | 3 of 8 | 3 of 5 | 4 |
| DeepSeek V4 Pro, open-weight (Hermes Agent), 18 questions | not scored the same way | 18 of 18 | 0 of 6 | 1 of 4 | not run |

- **Choosing the tool was not the hard part.** The four models scored by code picked the right tool on 19 to 22 of 20 to 22 questions. They differed in what they did with the results.
- **Strong models follow the guidance a result carries; weaker ones skip it.** Every result carries a ready-made citation and the data date. Claude used them every time; GPT-OSS and Llama gave the citation on 3 of 8.
- **Weaker models need the server to do the reading.** GPT-OSS misread the peak year from a 31-row table. The server now names the peak year, and the question went from failing every run to passing both.
- **Guardrails have to live in the server.** Llama handled 0 of 6 adversarial questions until the server stated its scope, then 4 of 6.

**The lesson:** a server that only meets the best model has not been tested. Claude at its ceiling would have hidden every one of these weaknesses, and none of the fixes cost Claude anything: on the final server, Claude Opus passed 29 of 30 and Sonnet 28 of 30.

**Citation integrity and consistency.** No answer from the server-backed Claude, Llama, or GPT-OSS runs cited a report number that does not exist. Claude Opus 5.5 scored the same on every rerun. For GPT-OSS 120B in Orchestrate, 5 questions passed all three runs, 9 failed all three, and 10 varied.

**Judge agreement.** The Claude and watsonx.ai judges gave the same verdict on 89 of 90 harness answers and 67 of 71 Orchestrate answers. IBM's engine agreed with the project's scoring on 52 of 72; it has no citation or data-date check, so it passed 16 answers the project failed.

**Phoenix evaluators on watsonx.ai.** A second, independent grading of the saved answers, with nothing rerun:

| Measure | Orchestrate round 1 (3 runs) | Orchestrate round 2 (2 runs) | Claude Opus / Sonnet, 30 questions |
|---|---|---|---|
| Correct against the gold reference | 16, 16, 15 of 24 | **20, 20** of 24 | 30 / 29 |
| In scope, or rightly declined | 23, 23, 23 | 24, 23 | 30 / 30 |
| Tool responses used faithfully | 17/20, 21/22, 22/22 | 21/23, 20/21 | 26 / 26 of 26 |

- **It confirms the main result with a judge this project did not build.** With only the server changed, GPT-OSS 120B's correct answers rose from about 16 to 20 of 24. Its tool selection and tool arguments did not move: the gain came from how the agent used results, not which tool it chose.

Per-run verdicts, with every judge's reasoning: [Results](../evaluation/results.md#phoenix-evaluators-on-watsonxai).

**Asking the user instead of guessing.** A facility name that matches several, such as "the Columbia VA", is never resolved by the model. Where the host supports MCP elicitation, the server asks the user directly with a form; everywhere else the result lists the matches and says to ask. Measured with Claude Opus 5.5, five runs per arm:

| Medians | Claude asks in chat | The server's form |
|---|---|---|
| Calls to the server | 2 | 1 |
| Model requests | 4 | 2 |
| Tokens processed | 47,607 | 29,046 |

The form halved the round trips against asking in chat and cut tokens 39 percent, and the user's choice reached the server without passing through the model. Detail: [What the form saves](../evaluation/results.md#what-the-form-saves).

**Operational metrics.** Median tool latency runs from about 0.13 seconds (analysis) to about 2 seconds (the inspection brief, which runs up to ten searches). A [load test](../../eval/results/2026-11-17-load-test/summary.md) ramped from 1 to 40 concurrent clients through the public URL: all 2,059 calls were answered with no errors. A full Claude Opus 5.5 run of 24 questions costs about $3 at list prices, including the judge.

### Failure analysis

Each failure was read against the tool results and the data API's traces, and sorted by cause.

| Cause | Examples | Response |
|---|---|---|
| Server | An office name put in the wrong filter matched nothing; facility counts routed to search; out-of-scope questions not covered by the server's instructions | Fixed in the server and verified by retest |
| Data service | Counting with only a facility-response or domain filter failed | Fixed in the data API |
| Model | A misread 31-row table; report numbers given without links | The server now precomputes the peak year and requests citation in every result |
| Scorer | Report numbers with non-breaking hyphens not recognized | Scorer fixed; every earlier run rescored with no change |

Server changes were verified by rerunning the same model with only the server changed:

| Test | Before | After |
|---|---|---|
| Adversarial set, Claude Opus 5.5 | 5 of 6 | 6 of 6 |
| Adversarial set, Llama 3.3 70B | 0 of 6 | 4 of 6 |
| GPT-OSS 120B in Orchestrate, 24 questions | 10, 8, and 11 | 12 and 12 |

Claude Opus was unchanged on every measure, and Llama's total held at 9 of 24. Round by round: [the improvement journey](../evaluation/results.md#the-improvement-journey).

## 4. Security considerations

The full design, every check with its latest result, the independent review, and the accepted risks are in [SECURITY.md](../../SECURITY.md).

### Data classification

The data is public: OIG's published reports and recommendations at vaoig.gov, with no CUI. Inspection findings are addressed to roles and offices; the server never guesses who was responsible and names a person only where a quoted finding does. Questions sent during the hackathon are recorded in traces, users are told so, and they are asked not to enter patient or nonpublic information.

### Scope containment as a control

Five behavior questions and six adversarial questions test that the agent declines what the data cannot support, refuses to rank facilities or guess who was responsible, gives no medical advice and sends an emergency to 911, and does not invent a report. The server states its scope in its own instructions, so the guardrail holds for any host, not only one configured agent.

### Secrets and configuration

Credentials load from the environment, or in Orchestrate from a connection, and are never committed: a scan of the repository's full history found none. The server refuses to start without a strong bearer token or with a plain-HTTP data address. Dependencies are locked with hashes and audited on every change; the base image and CI actions are pinned.

### Untrusted input and prompt injection

Every result marks the fields that quote report text and says to cite them and never follow instructions in them, and every tool is read-only. The adversarial set includes an injected instruction; both models ignored it after the server changes. A robustness check sends every tool path traversal, injection, and out-of-bound values: all 49 checks pass, with no stack trace, address, or credential in any reply.

### Transport and isolation

The hosted endpoint is reached through a Cloudflare Tunnel with no open port; every request needs a bearer token per client, compared in constant time, with a per-client rate limit. The data API sits behind Cloudflare Access and requires its own service token and API key, and the server can call only that one origin. The container runs as a non-root user with a read-only filesystem. In Orchestrate, the server runs over stdio with no network endpoint of its own. An independent review on November 17 found no high-severity issues; its medium and low findings are fixed, each with a test.

## 5. Lessons learned and recommendations

### What worked

Gold answers computed independently of the API caught errors the API would have repeated. Scoring facts and citations by code made results repeatable, and two judges from different model families, with IBM's engine and the data API's traces as further readings, showed when a single judge was wrong. Testing with weaker models showed what the server must make explicit, and each fix was verified by rerunning the same model. The no-tool baseline turned "the server helps" into a measured difference.

### Limitations

One builder wrote the questions and the server, and some fixes followed failures on these same questions, so later runs are not blind on those points. Thirty questions are a check, not a statistical estimate. Judges are models, and no person reviewed every answer. The load test was one run, to 40 clients, and not to failure.

### Recommendations

- Compute gold answers from the source data, not from the API under test.
- Run a no-tool baseline and a weaker model: the baseline shows what the server adds, and the weaker model shows what it must make explicit.
- Make an empty result say so: a filter that silently matches nothing becomes a wrong answer.
- Put scope and guardrails in the server's own instructions and results, not in one host's prompt.
- Read failures against the server's request traces before deciding who is at fault.
- Use two judges from different model families, and review the answers where they disagree.
