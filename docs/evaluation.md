# Evaluation

**Run:** November 4, 2026, against data snapshot `2bb10bd321e08dfc`, data as of the same date.
**Method in brief:** an AI assistant that knows nothing about this project answers 24 questions using only this server's tools, over authenticated HTTP. Its answers are scored against gold answers computed by SQL directly from the database.

## Results

These are the final runs, on the server as built today and the data snapshot the live API serves. On 2026-11-10, after typed results, one `notices` field, and a tool selection guide in the instructions, Claude Opus 5.5 was run again ([`eval/results/2026-11-10-opus-5-5/`](../eval/results/2026-11-10-opus-5-5/)). It was run again after the analysis changes from the Hermes assessment below. Both runs matched the earlier run on every measure, including tool selection (20 of 20) and caveats (14 of 14), with the same one failure; the folder holds the later run. Results for watsonx Orchestrate and its models are not included, because the server has not yet been deployed there.

| Measure | Claude Opus 5.5 | Claude Sonnet 5.5 | Scored by |
|---|---|---|---|
| Questions passing every check | 23 of 24 | 23 of 24 | Code and judge |
| Exact facts present in the answer | 16 of 16 questions | 16 of 16 questions | Code |
| Agrees with the gold reference | 24 of 24 | 23 of 24 | Judge |
| Right tool chosen | 20 of 20 | 20 of 20 | Code |
| Caveats and required behaviors | 14 of 14 | 14 of 14 | Judge |
| Every cited report number and link exists | 24 of 24 | 24 of 24 | Code |
| Report number and link given where required | 8 of 8 | 7 of 8 | Code |
| Data date stated where required | 5 of 5 | 5 of 5 | Code |
| List recall, the one question needing a complete list | 1.00 | 1.00 | Code |
| List precision, mean of three questions | 0.73 | 0.77 | Code |
| Tool errors | 0 | 0 | Code |
| Mean time per question | 15.3 s | 8.7 s | Code |
| Estimated cost of the run, including the judge | $2.87 | $1.31 | List prices |

**Neither model cited a report number that does not exist, in any run.** That is the project's stated target. The independent agent below wrote one wrong number.

### The failures, and what the scores do not show

**The one failed question, on both models,** asked for Durham's reports of two types, leaving out hotline and financial reports. Both listed all eight correctly and named the excluded reports under a "left out" heading. The scorer counts every report number in an answer, so it marked those as extras. Opus's answer is right in substance, but this is reported as a failure rather than adjusting the scorer after seeing the result.

**Sonnet's answer to that question also had real errors.** It said there were 9 such reports while listing 8, and it gave no links. The judge caught the miscount this time. In an earlier run, the same model made the same kind of error and the judge passed it, which shows the limit of the method: an answer can pass and still contain a small error.

**List precision is a strict figure.** On the search questions, it counts a report as relevant only if a recommendation contains the exact phrase "medication cart." Some extras were plausibly about related medication security, and were not reviewed one by one. It is not how often a search result is relevant. The separate [search comparison](mcp-overview.md) is the relevance test, where a full sentence was relevant 44 percent of the time.

## What was measured

| Category | Questions | What they test |
|---|---|---|
| Exact | 14 | Counts, closure measures, aging, one facility, including one inspected with no recommendations, one report, recurring findings |
| List | 2 | Top offices by open items; one facility's inspection reports |
| Search | 2 | A plain-language question, and what facilities committed to do |
| Workflow | 1 | Preparing a facility for inspection |
| Behavior | 5 | An ambiguous facility, a question the data cannot answer, a request for a miss rate, a request to rank facilities, a request to predict findings |

The full set, with answers, is in [`eval/gold/questions.json`](../eval/gold/questions.json).

**Gold answers do not come from the API.** [`eval/gold/build_gold.py`](../eval/gold/build_gold.py) queries the snapshot directly, opened read-only, and stops if its checksum differs from the pinned one. The API serves that same file, byte for byte. Answers built from the tools matched these queries on all 16 fact questions, so the evaluation also checks the API independently on those facts. One gold question reads the same full-text index the API uses, because what counts as a matching word is defined by that index.

**The assistant gets no project-specific prompt.** Its system prompt is the server's own `instructions` field, as any MCP host would receive. So the scores reflect what the tools and their descriptions communicate. It connects over HTTP with the bearer token, so every question also exercises the deployed authentication path.

**Scoring is by code wherever possible.** Code checks facts, lists, tool choice, and citations against the snapshot's 4,415 report listings. A separate run of Claude Opus 5.5 judges only what code cannot: caveats, behaviors, and overall agreement with the gold reference. The harness refuses to run if the server's data date or counts do not match the pinned snapshot.

Traces, datasets, and experiments are recorded in Arize Phoenix. Run records and per-question results are in [`eval/results/`](../eval/results/). To reproduce a run, see [`eval/README.md`](../eval/README.md).

## An independent client: DeepSeek through Hermes Agent

A separate agent, Hermes Agent running DeepSeek V4 Pro 0813, answered 18 of the questions over public HTTPS, on the final server and data. It logged a longer answer, its tools, and its observations, because the tester asked for them. The tester then asked it to add a native answer to each question, the answer it would have given if simply asked. These are in the [test bank](https://www.troymd.com/mcp-hackathon-test-bank) and [`qna2.md`](../eval/results/2026-11-04-hermes-deepseek-native/qna2.md), and scores are in [`eval/results/`](../eval/results/).

| Measure | Native answers | Longer logged answers |
|---|---|---|
| Exact facts present | 11 of 11 | 11 of 11 |
| Agrees with the gold reference | 18 of 18 | 18 of 18 |
| Caveats and behaviors | 12 of 13 | 10 of 13 |
| Report numbers that do not exist | 0 | 1 |
| Data date stated, where required | 1 of 4 | 4 of 4 |
| Report number and link together, where required | 0 of 6 | 0 of 6 |

**This was not a blind or isolated run, and the native answers are not a fresh one.** The agent had access to its first-round answers, ran across several sessions, and wrote the native answers mostly from its own log, with few new tool calls. It was told to leave out metadata, which may be why links and dates are missing. Its tool results did carry report links and the citation line. Isolated Claude runs gave a number and link on 15 of 16 required answers.

**The one wrong number,** 26-00254-277 for report 25-00254-277, is in a logged answer. No native answer repeats it, and no Claude run produced a report number that does not exist.

Reading the answers by hand also found overreach the judge passed, such as calling a recommendation "the cheapest insurance available." A model can still go beyond what the tools return, whatever the server says.

## What the evaluation changed

The first run found problems, the Hermes test found more, and checking those answers found backend defects. The numbers above come from the final run, after all of it. Earlier results are kept in [`eval/results/superseded-d364ff4c/`](../eval/results/superseded-d364ff4c/).

| What was found | Finding | Change |
|---|---|---|
| Sonnet gave "about 86%" as a miss rate while warning against it | **A server problem.** The analysis tool returned closed-after-target counts, so a model could compute a rate the data cannot support. A warning was not enough | Removed those counts from the tool |
| The tool's cited source page, `recommendations-all`, marked as an unknown link | A scorer error. It is a real OIG page | Added it to the known pages |
| A correct answer about El Paso marked as missing a fact | A scorer error. The pattern did not accept the word "no" | Widened the pattern |
| Durham question asked for "every inspection" | A question error. OIG's hotline reports are also inspections, so the gold list was too narrow | Reworded it by report type, and recomputed the gold answer from those types |

| DeepSeek gave report numbers but no links | **A server problem.** The host appears not to pass the server's instructions to its model | Each tool result now says how to cite it |
| Inspections with no recommendations were missing, so VA North Texas showed a next window of February 2025 after a report published in October 2026 | **A backend defect,** affecting the estimates of 25 facilities | Fixed in the data service, with a question added on this case |
| Page footers and split words in extracted text, such as "r andom checks" | **A backend defect** | Fixed. Corrective actions with a footer went from 1,813 to 1, and split words from 13,392 to 60 |
| The same report listed twice, and aliases shared between stations | **A backend review.** 5 of 15 report pairs were one report listed twice, and 7 of 10 aliases were errors | Duplicates flagged, and wrong links corrected |
| On 2026-11-10, Hermes Agent broke a mental-health trend out by VISN in 23 calls, matched results to VISNs by position, and summed per-topic rows by hand | **A server problem.** Analysis results did not name the filters that produced them, nothing said that a third of those recommendations carry no VISN (623 of 920 attributed), and the description did not say how to count one topic | Results echo their filters and keywords, a VISN or state filter carries a notice about what it leaves out, a year grouping states its exact total, and the description says to count one topic by year. The backend then found that VISN labels changed meaning in August 2026, when VA replaced its 18 networks with five and OIG did not retag older reports, so VISN filters and facility results now say so and point to state for following a region. Grouping by facility stays refused, and grouping by VISN was not added |

Because these changes followed earlier results, the final run is not a blind test of those points. The gold set was written by the same person who built the system, knowing its strengths. The question about a miss rate, in particular, was passed after a fix made for that question.

## Response design

**Structured JSON only.** The MCP builder guidance suggests a `response_format` parameter offering JSON or Markdown. The tools return structured JSON only, by decision. Each result carries fields a model must keep separate from prose: provenance and how to cite it, notices to pass on, pagination, and which fields quote report text. The DeepSeek finding above shows the risk of relying on anything outside the result: that host dropped the server's instructions, and citations came back only once each result carried its own. Markdown would double the response surface of seven tools and invite a model to paraphrase notices away. If a client needs Markdown, one renderer over the typed results below could add it.

**Typed results.** Each tool declares an output schema built from Pydantic models in `models.py`, and MCP clients check every successful result against it. Fields the server writes are typed exactly. Records passed through from the data API allow extra fields and nulls, so the API can add a field without breaking a client. A check of 76 live calls across all seven tools found no result outside its schema.

**One field for pass-on text.** Text the server adds for the user is always in `notices`, a list present on every data result (a "not found" or "several match" answer has a hint instead). Text the data API writes about its own data stays beside that data in a field ending `_basis`, such as `next_window_basis`. The server instructions, tool descriptions, and prompts all name those two.

## Known limits

**Estimates for clean inspections start later.** A report with no recommendations gives no inspection dates, so its next-window estimate counts from the publication date, which usually comes months after the inspection. 15 facilities have an estimate already past, which does not mean they are overdue, and the tools say so.

**Small test set, and one builder.** 24 questions are a check, not a statistical estimate. Results may vary between runs, because the models do not accept a fixed seed.

**The judge is the same model family as the agent.** It is not independent confirmation. No person reviewed every answer.

**watsonx Orchestrate's model has not been tested,** and these results do not transfer to it automatically.

**Not tested:**

- Sustained load. Latency below is from a handful of calls, not a load test.
- Calls from IBM's network.
- Any question about report narrative in PDF pages beyond what the tools return in search results.

## Tool latency

Measured through the server, in the container that IBM will run, against the hosted API, during the 2026-11-10 Opus run. That run followed two changes that cut round trips: one pooled HTTP client instead of a new connection per call, and dataset status reading its five filter lists at once. Sample sizes are small. The status and brief tools make several API calls each, and the brief runs up to ten searches.

| Tool | Calls | Median | Slowest |
|---|---|---|---|
| `vaoig_analyze_recommendations` | 16 | about 0.13 s | about 0.24 s |
| `vaoig_find_systemic_clusters` | 3 | about 0.15 s | about 0.24 s |
| `vaoig_get_dataset_status` | 23 | about 0.27 s | about 0.40 s |
| `vaoig_get_facility_profile` | 8 | about 0.29 s | about 0.38 s |
| `vaoig_get_inspection_brief` | 2 | about 2.0 s | about 2.0 s |
| `vaoig_get_report` | 1 | about 0.24 s | about 0.24 s |
| `vaoig_search_findings` | 4 | about 0.32 s | about 0.36 s |

The 2026-11-04 runs were slower, for example 2.7 s for dataset status and 2.8 s for the brief, but they ran soon after the backend machine restarted, so the difference is not all from these changes. A controlled comparison on 2026-11-10, alternating per-call and pooled clients against the same API, put the pooled client's gain at about 30 percent for search and 50 percent for dataset status.

## Authentication tests

Run against the same container, and again through a temporary public HTTPS tunnel. All passed. [`deploy/verify_deployment.py`](../deploy/verify_deployment.py) and [`deploy/verify_image.sh`](../deploy/verify_image.sh) repeat them.

| Connection | Refused | Accepted |
|---|---|---|
| Client to MCP server | No credentials; wrong token; right token one character short; right token as Basic; token in a custom header; Cloudflare token in its own headers or as a bearer token | The right bearer token |
| MCP server to data API | No credentials; wrong Cloudflare token; the MCP bearer token | The right Cloudflare token |

The server refuses to start without a bearer token, with one under 32 characters, or with a plain-HTTP remote API. With a missing or wrong Cloudflare token, it starts, and its tools return a short refusal that does not reveal the API's address. No secret appeared in tool responses, server logs, or the image.

Local HTTP binds `127.0.0.1` and checks Host and Origin headers. Tested 2026-11-10 against a live local server: a foreign Host header got 421, a foreign Origin 403, and a request without a token 401. The container path listens on all interfaces behind Cloudflare and the bearer token, and the deployment check above still passes against it.
