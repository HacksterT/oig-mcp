# Evaluation

**Run:** November 4, 2026, against data snapshot `d364ff4cb215c6d8`, data as of the same date.
**Method in brief:** an AI assistant that knows nothing about this project answers 23 questions using only this server's tools, over authenticated HTTP. Its answers are scored against gold answers computed by SQL directly from the database.

## Status of these results

The runs below predate the last changes: smaller responses, a citation line in each result, and clearer notes on missing responses and OIG's totals. Backend fixes are also on the way, with a new snapshot. **Both models will be rerun on the final server and data, and this document updated.** Until then, read these as the most recent results, not the final ones.

## Results

Results for watsonx Orchestrate and its models are not included, because the server has not yet been deployed there.

| Measure | Claude Opus 5.5 | Claude Sonnet 5.5 | Scored by |
|---|---|---|---|
| Questions passing every check | 22 of 23 | 22 of 23 | Code and judge |
| Exact facts present in the answer | 15 of 15 questions | 15 of 15 questions | Code |
| Agrees with the gold reference | 23 of 23 | 23 of 23 | Judge |
| Right tool chosen | 19 of 19 | 19 of 19 | Code |
| Caveats and required behaviors | 13 of 13 | 13 of 13 | Judge |
| Every cited report number exists in the data | 23 of 23 | 23 of 23 | Code |
| Every cited link is a real OIG page | 23 of 23 | 22 of 23 | Code |
| Citation given where required | 7 of 7 | 7 of 7 | Code |
| Data date stated where required | 5 of 5 | 5 of 5 | Code |
| List recall, the one question needing a complete list | 1.00 | 1.00 | Code |
| List precision, mean of three questions | 0.71 | 0.65 | Code |
| Tool errors | 0 | 0 | Code |
| Mean time per question | 14.5 s | 7.7 s | Code |
| Estimated cost of the run, including the judge | $2.77 | $1.38 | List prices |

**No report number was fabricated in any answer, in any run.** That is the project's stated target, and it held.

### The failures, and what the scores do not show

**The one failed question, on both models,** asked for Durham's reports of two types, leaving out hotline and financial reports. Both listed all nine correctly and named the excluded reports under a "left out" heading. The scorer counts every report number in an answer, so it marked those as extras. The answers are right in substance, but this is reported as a failure rather than adjusting the scorer after seeing the result.

**List precision looks low for a similar reason.** It counts a report as relevant only if a recommendation contains the exact phrase "medication cart." Some extras were plausibly about related medication security, and were not reviewed one by one. Treat 0.71 and 0.65 as strict lower-end figures, not as how often a search result is relevant. The separate [search comparison](mcp-overview.md) is the relevance test, and it found about half of the results relevant.

**Sonnet's invalid link** was a placeholder it wrote, `https://www.vaoig.gov/reports/<report-type>/<slug>`, describing how links are built. It was not presented as a citation.

**A miscount the scoring missed.** Sonnet wrote that Durham has "10" such reports while listing the correct 9. The code checks the list, and the judge passed it. This shows the limit of the method: an answer can pass and still contain a small error.

## What was measured

| Category | Questions | What they test |
|---|---|---|
| Exact | 13 | Counts, closure measures, aging, one facility, one report, recurring findings |
| List | 2 | Top offices by open items; one facility's inspection reports |
| Search | 2 | A plain-language question, and what facilities committed to do |
| Workflow | 1 | Preparing a facility for inspection |
| Behavior | 5 | An ambiguous facility, a question the data cannot answer, a request for a miss rate, a request to rank facilities, a request to predict findings |

The full set, with answers, is in [`eval/gold/questions.json`](../eval/gold/questions.json).

**Gold answers do not come from the API.** [`eval/gold/build_gold.py`](../eval/gold/build_gold.py) queries the snapshot directly, opened read-only, and stops if its checksum differs from the pinned one. The API serves that same file, byte for byte. Answers built from the tools matched these queries on all 15 fact questions, so the evaluation also checks the API independently on those facts. One gold question reads the same full-text index the API uses, because what counts as a matching word is defined by that index.

**The assistant gets no project-specific prompt.** Its system prompt is the server's own `instructions` field, as any MCP host would receive. So the scores reflect what the tools and their descriptions communicate. It connects over HTTP with the bearer token, so every question also exercises the deployed authentication path.

**Scoring is by code wherever possible.** Code checks facts, lists, tool choice, and citations against the snapshot's 4,415 reports. A separate run of Claude Opus 5.5 judges only what code cannot: caveats, behaviors, and overall agreement with the gold reference. The harness refuses to run if the server's data does not match the pinned snapshot.

Traces, datasets, and experiments are recorded in Arize Phoenix. Run records and per-question results are in [`eval/results/`](../eval/results/). To reproduce a run, see [`eval/README.md`](../eval/README.md).

## An independent client: DeepSeek through Hermes Agent

A separate agent, Hermes Agent running DeepSeek V4 Pro 0813, answered 17 of the questions over a public HTTPS address. It ran as one continuing session writing to a file, so it is not directly comparable with the isolated runs above. Results are in [`eval/results/2026-11-04-hermes-deepseek-v4-pro-0813/`](../eval/results/2026-11-04-hermes-deepseek-v4-pro-0813/), and the answers are in [`qna.md`](qna.md).

| Measure | Result |
|---|---|
| Exact facts present | 10 of 10 |
| Agrees with the gold reference | 17 of 17 |
| Caveats and behaviors | 11 of 12 |
| Every cited report number exists | 17 of 17 |
| Report number and link together, where required | 0 of 5 |
| Data date stated, where required | 2 of 4 |

It gave report numbers in those five answers, but no links, and the host appears not to pass the server's instructions to its model. That is why each tool result now says how to cite it. Reading the answers by hand also found overreach the judge passed, such as calling open findings "the single most likely things to be re-cited." A model can still go beyond what the tools return, whatever the server says.

## What the evaluation changed

Two runs happened. The first found problems, and the numbers above come from the second. The first run's results are kept in [`eval/results/baseline/`](../eval/results/baseline/).

| First run | Finding | Change |
|---|---|---|
| Sonnet gave "about 86%" as a miss rate while warning against it | **A server problem.** The analysis tool returned closed-after-target counts, so a model could compute a rate the data cannot support. A warning was not enough | Removed those counts from the tool |
| The tool's cited source page, `recommendations-all`, marked as an unknown link | A scorer error. It is a real OIG page | Added it to the known pages |
| A correct answer about El Paso marked as missing a fact | A scorer error. The pattern did not accept the word "no" | Widened the pattern |
| Durham question asked for "every inspection" | A question error. OIG's hotline reports are also inspections, so the gold list was too narrow | Reworded it by report type, and recomputed the gold answer from those types |

While checking that last question, the evaluation also found a backend defect that **no question scores**. See known limits.

Because these changes followed the first results, the second run is not a blind test of those points. The gold set was written by the same person who built the system, knowing its strengths. The question about a miss rate, in particular, was passed after a fix made for that question.

## Known limits

**A defect being fixed: inspections with no recommendations.** These reports are missing from the backend's inspection table. For about 14 facilities, the latest inspection and next-window estimate are therefore too early, sometimes already past. VA North Texas was inspected in a report published October 2026, and its estimate reads February 2025. The gold questions use El Paso and Durham, which this does not affect. A question on this case will be added when it is fixed.

**Small test set, and one builder.** 23 questions are a check, not a statistical estimate. Results may vary between runs, because the models do not accept a fixed seed.

**The judge is the same model family as the agent.** It is not independent confirmation. No person reviewed every answer.

**watsonx Orchestrate's model has not been tested,** and these results do not transfer to it automatically.

**Not tested:**

- Sustained load. Latency below is from a handful of calls, not a load test.
- Calls from IBM's network.
- Any question about report narrative in PDF pages beyond what the tools return in search results.

## Tool latency

Measured through the server, in the container that IBM will run, against the hosted API. Sample sizes are small.

| Tool | Median, Opus run | Slowest in either run |
|---|---|---|
| `vaoig_analyze_recommendations` | about 0.2 s | about 0.4 s |
| `vaoig_find_systemic_clusters` | about 0.3 s | about 0.3 s |
| `vaoig_get_dataset_status` | about 1.2 s | about 1.6 s |
| `vaoig_get_facility_profile` | about 0.5 s | about 0.5 s |
| `vaoig_get_inspection_brief` | about 1.9 s | about 1.9 s |
| `vaoig_get_report` | about 0.4 s | about 0.5 s |
| `vaoig_search_findings` | about 0.4 s | about 0.5 s |

## Authentication tests

Run against the same container, and again through a temporary public HTTPS tunnel. All passed. [`deploy/verify_deployment.py`](../deploy/verify_deployment.py) and [`deploy/verify_image.sh`](../deploy/verify_image.sh) repeat them.

| Connection | Refused | Accepted |
|---|---|---|
| Client to MCP server | No credentials; wrong token; right token one character short; right token as Basic; token in a custom header; Cloudflare token in its own headers or as a bearer token | The right bearer token |
| MCP server to data API | No credentials; wrong Cloudflare token; the MCP bearer token | The right Cloudflare token |

The server refuses to start without a bearer token, with one under 32 characters, or with a plain-HTTP remote API. With a missing or wrong Cloudflare token, it starts, and its tools return a short refusal that does not reveal the API's address. No secret appeared in tool responses, server logs, or the image.
