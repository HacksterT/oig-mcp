# Testing results

*What the testing found. How it was done is in [testing-architecture.md](testing-architecture.md). All results use the data snapshot `2bb10bd321e08dfc`, data as of November 4, 2026. Run records are in [`eval/results/`](../eval/results/).*

## Summary

| Platform | Result | Read it with |
|---|---|---|
| Claude Opus 5.5, harness | 23 of 24 questions pass every check; matched on reruns on November 10 | The same builder wrote the questions; the failure is a scoring call on a correct answer |
| Claude Sonnet 5.5, harness | 23 of 24 | Its answer to the failed question also miscounted |
| DeepSeek V4 Pro 0813, Hermes Agent | All 18 answers agree with the gold reference; all 11 exact facts present | Not a blind run; answers rarely gave links |
| IBM agent in watsonx Orchestrate, first six questions | 5 of 6 correct at first; the sixth fixed in the server and confirmed in Orchestrate | Read against the gold answers and the data API's traces, not yet by a judge |
| IBM agent in watsonx Orchestrate, 24 questions, three runs | Pending | See below |
| Automated tests | 197 pass, on every change | |
| Image and deployment checks | 15 of 15 and 22 of 22, on the Mac and on IBM's virtual machine | Not a load test |

No Claude run cited a report number that does not exist, which is the project's stated target. The only one found on any platform is in a logged answer from the Hermes agent, described below. All eight report numbers in Orchestrate's first answers exist in the snapshot, and the three-run answers will be checked the same way.

## Claude

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

Both models ran on November 4. Claude Opus 5.5 was run again on November 10, after typed results, the single `notices` field, and a tool selection guide were added, and again after the analysis changes that followed the Hermes assessment. Both reruns matched the first on every measure, with the same one failure. Answers built from the tools also matched the SQL gold answers on all 16 fact questions, so the evaluation checks the API independently on those facts.

**The failure is kept as a failure.** The question asked for every Healthcare Facility Inspection or Comprehensive Healthcare Inspection Program report for Durham, leaving out hotline and financial reports. Both models listed all eight correctly and also named the excluded reports under a "left out" heading. The scorer counts every report number in an answer, so it marked those as extras. Claude Opus 5.5's answer is right in substance, but the scorer was not changed after seeing the result.

**Sonnet's answer to that question also had real errors.** It said there were 9 such reports while listing 8, and gave no links. The judge caught the miscount. In an earlier run the same model made the same kind of error and the judge passed it: an answer can pass and still contain a small error.

**List precision is a strict figure.** On the search questions, a report counts as relevant only if a recommendation contains the exact phrase "medication cart." It is not how often a search result is relevant; the separate [search comparison](mcp-overview.md) tested that, and a full sentence was relevant 44 percent of the time.

## DeepSeek through Hermes Agent

Hermes Agent, running DeepSeek V4 Pro 0813, answered 18 of the questions over public HTTPS on the final server and data. It logged a longer answer and its observations, then gave a native answer, the one it would have given if simply asked. Both are in the [test bank](https://www.troymd.com/mcp-hackathon-test-bank).

| Measure | Native answers | Longer logged answers |
|---|---|---|
| Exact facts present | 11 of 11 | 11 of 11 |
| Agrees with the gold reference | 18 of 18 | 18 of 18 |
| Caveats and behaviors | 12 of 13 | 10 of 13 |
| Report numbers that do not exist | 0 | 1 |
| Data date stated, where required | 1 of 4 | 4 of 4 |
| Report number and link together, where required | 0 of 6 | 0 of 6 |

This was not a blind or isolated run. The agent could see its first-round answers, worked across several sessions, and wrote the native answers mostly from its own log. It was told to leave out metadata, which may explain the missing links and dates, though its tool results carried both. The one wrong number, 26-00254-277 for report 25-00254-277, is in a logged answer. Reading the answers by hand also found overreach the judge passed, such as calling a recommendation "the cheapest insurance available": a model can still go beyond what the tools return.

## watsonx Orchestrate

### First six questions

After deployment, the agent was asked the six check questions from the deployment handoff, with the same tools and single instruction it has had throughout. The answers were read against the gold answers, and the data API's traces confirm the tool calls.

| Question | Result |
|---|---|
| Dataset status | Correct: data as of November 4, 2026, 4,415 report listings, 15,649 recommendations, and why OIG's dashboard shows 586 open against this data's 567 |
| Healthcare Facility Inspection recommendations in 2026 | Correct: 148, with 80 open |
| Unlocked medication carts | Correct: eight reports cited with vaoig.gov links and the data date |
| Preparing El Paso for inspection | Correct: used the inspection brief, labeled the next window as an estimate, and predicted no findings |
| What OIG found at "the New York VA" | **Failed:** said there were no findings |
| Share of VHA recommendations that missed their targets | Correct: gave no percentage and said the data cannot establish it |

**The failure and its fix.** The traces showed the agent never called the facility tool. It searched for the word "findings" filtered to state `NY`, which matched nothing, and reported no findings. The causes were all in the server: the tool descriptions did not send a question about one named place to the facility tool; the facility lookup matched only text that appears in a facility's name, and no facility is named "New York VA"; and the state filter expected "New York" and silently matched nothing for "NY." The server now routes such questions to the facility tool, retries a lookup once without words such as "VA" or "medical center," and accepts postal codes. After the fix, the same question called the facility tool, retried with "New York," and returned ten matching facilities, so the agent could ask which was meant. An Orchestrate evaluation of that saved test reported journey success, tool call precision and recall of 1, one tool call, and a response time of 5.8 seconds.

**A lesson for the test design.** A saved Orchestrate test expects every tool call its recording made. When the first question was saved, the agent had called both the analysis tool and the dataset status tool; in the evaluation run it answered correctly with the analysis tool alone, and the test failed on recall. The tests now name only the call on each question's critical path.

### 24 questions, three runs (pending)

This section will report the 24 questions run three times against the agent with IBM's Agent Development Kit, each run read three ways: IBM's evaluation engine (journey success, tool call precision and recall, text match, keywords, and each behavior check's verdict), the project's scoring of the same answers against the gold, and the data API's traces for each run's time window. It will report how often the two judges agreed, each disagreement and which judge was right, and which questions failed consistently rather than once.

## What testing changed

Testing changed the server, the scorer, and the data, not only the scores. Because these changes followed earlier results, later runs are not blind tests of those points; the question about a miss rate, in particular, was passed after a fix made for that question. Earlier results are kept in [`eval/results/superseded-d364ff4c/`](../eval/results/superseded-d364ff4c/).

| What was found | Kind | Change |
|---|---|---|
| Sonnet gave "about 86%" as a deadline miss rate while warning against it | Server | The analysis tool no longer returns closed-after-target counts, so no model can compute that rate |
| DeepSeek gave report numbers without links; its host did not pass the server's instructions to the model | Server | Each tool result carries its own citation line |
| Hermes Agent matched 23 parallel results to VISNs by position and summed rows that overlap | Server | Analysis results name their filters; VISN and state filters say what they leave out; a year grouping states its exact total. The data service then found VISN labels changed meaning in August 2026, so VISN filters now say so and point to state |
| Hints steering a model to the right tool sat in each description's Returns section, which FastMCP drops before sending ([#30](https://github.com/HacksterT/oig-mcp/pull/30)) | Server | The hints moved into the description proper |
| The image built on IBM's virtual machine could not import the server ([#33](https://github.com/HacksterT/oig-mcp/pull/33)) | Server | Files in the image are made readable whatever the build machine's permissions |
| The first Orchestrate registration ran the server with no data API address ([#35](https://github.com/HacksterT/oig-mcp/pull/35)) | Deployment | The toolkit passes the data API's settings through a key_value connection |
| The "New York VA" failure in Orchestrate ([#37](https://github.com/HacksterT/oig-mcp/pull/37)) | Server | Place questions route to the facility tool; facility lookups retry without generic words; state filters accept postal codes |
| VA North Texas showed a next window of February 2025 after a report published in October 2026 | Data | Inspections with no recommendations, missing for 25 facilities, were added; a question on this case joined the gold set |
| Page footers and split words in extracted text, such as "r andom checks" | Data | Corrective actions with a footer went from 1,813 to 1, and split words from 13,392 to 60 |
| The same report listed twice, and aliases shared between stations | Data | 5 of 15 report pairs were one report listed twice, and 7 of 10 aliases were errors; duplicates flagged and links corrected |
| The tool's cited source page marked as an unknown link | Scorer | It is a real OIG page; added to the known pages |
| A correct answer about El Paso marked as missing a fact | Scorer | The pattern did not accept the word "no"; widened |
| The Durham question asked for "every inspection" | Question | OIG's hotline reports are also inspections, so the gold list was too narrow; reworded by report type and recomputed |

## Speed

Measured through the server, in its container on the Mac, against the hosted data API, during the November 10 Claude Opus 5.5 run. Sample sizes are small.

| Tool | Calls | Median | Slowest |
|---|---|---|---|
| `vaoig_analyze_recommendations` | 16 | about 0.13 s | about 0.24 s |
| `vaoig_find_systemic_clusters` | 3 | about 0.15 s | about 0.24 s |
| `vaoig_get_dataset_status` | 23 | about 0.27 s | about 0.40 s |
| `vaoig_get_facility_profile` | 8 | about 0.29 s | about 0.38 s |
| `vaoig_get_inspection_brief` | 2 | about 2.0 s | about 2.0 s |
| `vaoig_get_report` | 1 | about 0.24 s | about 0.24 s |
| `vaoig_search_findings` | 4 | about 0.32 s | about 0.36 s |

The status and brief tools make several API calls each, and the brief runs up to ten searches. One pooled HTTP client, and dataset status reading its five filter lists at once, cut about 30 percent from search and 50 percent from dataset status in a controlled comparison. In Orchestrate the server runs over stdio and starts afresh for each call; starting it took about two seconds in a test on the Mac. Of the 5.8 seconds measured for the New York question, the data API's part was about 0.16 seconds, and the rest was Orchestrate's model and the process start. The service has not been load tested.

## Security

All authentication checks passed against the container, through a public HTTPS tunnel, and on IBM's virtual machine, where the image built there passed all 15 image checks, including the 22 deployment checks run against it. That run also confirmed IBM's network reaches the data API through Cloudflare with no proxy.

| Connection | Refused | Accepted |
|---|---|---|
| Client to MCP server | No credentials; wrong token; right token one character short; right token as Basic; token in a custom header; Cloudflare token in its own headers or as a bearer token | The right bearer token |
| MCP server to data API | No credentials; wrong Cloudflare token; the MCP bearer token; the Cloudflare token without the data API key | The Cloudflare token with the data API key |

The server refuses to start without a bearer token, with one under 32 characters, or with a plain-HTTP remote data address. With wrong data API credentials it starts, and its tools return a short refusal that does not reveal the API's address. No secret appeared in tool responses, logs, or the image. Local HTTP binds `127.0.0.1` and checks Host and Origin headers: tested against a live local server, a foreign Host header got 421, a foreign Origin 403, and a request without a token 401.

In Orchestrate the server runs over stdio inside Orchestrate's runtime, so it has no network endpoint to protect; its data API settings come from an Orchestrate connection, not from a file.

## A known limit of the data

**Estimates for clean inspections start later.** A report with no recommendations gives no inspection dates, so its next-window estimate counts from the publication date, which usually comes months after the inspection. 15 facilities have an estimate already past, which does not mean they are overdue, and the tools say so.
