# Testing results

*What the testing found. How it was done is in [testing-architecture.md](testing-architecture.md). Full tables for the Claude and Hermes runs are in [evaluation.md](evaluation.md). All results use the data as of November 4, 2026.*

## Summary

| Platform | Result | Read it with |
|---|---|---|
| Claude Opus 5.5, harness | 23 of 24 questions pass every check, matched again on November 10 after the last response changes | The same builder wrote the questions, and the failure is a scoring call on a correct answer |
| Claude Sonnet 5.5, harness | 23 of 24 | Its answer to the failed question also miscounted |
| DeepSeek V4 Pro 0813, Hermes Agent | 18 of 18 answers agree with the gold reference; all 11 exact facts present | Not a blind run; answers rarely gave links |
| IBM agent in watsonx Orchestrate, first six questions | 5 of 6 correct at first; the sixth fixed in the server and confirmed in Orchestrate | Checked by hand and in the data API's traces, not yet by a judge |
| IBM agent in watsonx Orchestrate, 24 questions, three runs | Pending | See the section below |
| Automated tests | 197 pass, on every change | |
| Image and deployment checks | 15 of 15 and 22 of 22, on the Mac and on IBM's virtual machine | Not a load test |

No Claude run cited a report number that does not exist. The only one found so far is in a logged answer from the Hermes agent, described below. The Orchestrate answers are checked for this in the three-run scoring.

## Claude

Both Claude models passed 23 of 24 questions on the frozen data. Claude Opus 5.5 was run again on November 10, after typed results, the single `notices` field, and the tool selection guide were added, and again after the analysis changes from the Hermes assessment. Both reruns matched the first on every measure, including tool selection (20 of 20) and caveats and required behaviors (14 of 14), with the same one failure. Exact facts were present on all 16 fact questions for both models, every cited report number and link existed (24 of 24), and neither model cited a report number that does not exist in any run.

**The failure is kept as a failure.** The question asked for every Healthcare Facility Inspection or Comprehensive Healthcare Inspection Program report for Durham, leaving out hotline and financial reports. Both models listed all eight correctly, and also named the excluded reports under a "left out" heading. The scorer counts every report number in an answer, so it marked those as extras. The answer from Claude Opus 5.5 is right in substance, but the scorer was not changed after seeing the result. Claude Sonnet 5.5's answer also said there were 9 reports while listing 8, and gave no links. The judge caught that miscount. In an earlier run the same kind of error passed the judge, which shows the method's limit: an answer can pass and still hold a small error.

List precision, 0.73 to 0.77 across runs, is strict: a search result counts only if a recommendation contains the exact phrase "medication cart." It is not a measure of how often results are relevant. That was tested separately, where a full sentence was relevant 44 percent of the time, as described in the [MCP overview](mcp-overview.md).

## DeepSeek through Hermes Agent

Hermes Agent, running DeepSeek V4 Pro 0813, answered 18 questions over public HTTPS. Every exact fact was present (11 of 11) and every answer agreed with the gold reference (18 of 18). Its native answers kept caveats and behaviors on 12 of 13, but stated the data date on only 1 of 4 where required and gave a report number with its link on 0 of 6. It was told to leave out metadata, which may explain the missing links and dates, though its tool results carried both.

This was not a blind or isolated run: the agent could see its earlier answers and worked across several sessions. One logged answer gave report 26-00254-277 for 25-00254-277, the only report number that does not exist in any run on any platform. Reading the answers by hand also found overreach the judge passed, such as calling a recommendation "the cheapest insurance available."

## watsonx Orchestrate

### First six questions

After deployment, the agent in Orchestrate was asked the handoff's six check questions. The answers were read against the gold answers, and the data API's traces confirm the tool calls.

| Question | Result |
|---|---|
| Dataset status | Correct: data as of November 4, 2026, 4,415 report listings, 15,649 recommendations, and the reason OIG's dashboard shows 586 open against this data's 567 |
| Healthcare Facility Inspection recommendations in 2026 | Correct: 148, with 80 open |
| Unlocked medication carts | Correct: eight reports cited with vaoig.gov links and the data date |
| Preparing El Paso for inspection | Correct: used the inspection brief, labeled the next window as an estimate, and predicted no findings |
| What OIG found at "the New York VA" | **Failed:** said there were no findings |
| Share of VHA recommendations that missed their targets | Correct: gave no percentage and said the data cannot establish it |

**The failure and its fix.** The traces showed the agent never called the facility tool. It searched for the word "findings" filtered to state `NY`, which matched nothing, and reported that as no findings. Three causes, all in the server:

1. The tool descriptions did not send a question about one named place to the facility tool.
2. The facility lookup matched only text that appears in a facility's name, and no facility is named "New York VA."
3. The state filter expected "New York" and silently matched nothing for "NY."

The server now routes such questions to the facility tool, retries a lookup once without words such as "VA" or "medical center," and accepts postal codes. After the fix was registered in Orchestrate, the same question at 21:12 UTC on November 16 called the facility tool, retried with "New York," and returned ten matching facilities, so the agent could ask which was meant. An Orchestrate evaluation of that saved test reported journey success, tool call precision and recall of 1, one tool call, and a response time of 5.8 seconds.

**One lesson for the test design.** A saved Orchestrate test expects every tool call its recording made. When the first question was saved, the agent had called both the analysis tool and the dataset status tool. On the evaluation run it answered correctly with the analysis tool alone, and the test failed on recall. The tests now name only the call on each question's critical path.

### Orchestrate evaluation, three runs (pending)

This section will report the 24 questions run three times against `gsa-oig-assist-TES` with IBM's Agent Development Kit, each run read three ways:

- **IBM's evaluation engine:** journey success, tool call precision and recall, text match, keywords, and each behavior check's verdict, per run and across the three runs.
- **The project's scoring:** the same answers scored against the gold answers with the code checks and judge used for Claude, so the platforms compare directly.
- **The data API's traces:** the tools actually called for each question, matched to each run's start and end times.

It will also report how often the two judges agreed, each disagreement and which judge was right, and which questions failed consistently rather than once.

## What testing changed in the server

Testing changed the server, not only the scores. Each change below was prompted by a test result.

| Change | Prompted by |
|---|---|
| The analysis tool no longer returns closed-after-target counts | Claude Sonnet 5.5 computed a miss rate of "about 86%" from them while warning against it |
| Each tool result carries its own citation line | DeepSeek gave report numbers without links; its host did not pass the server's instructions to the model |
| Analysis results name their filters, and VISN and state filters carry notices on what they leave out | Hermes Agent matched 23 parallel results to VISNs by position and summed rows that overlap |
| Hints that steer a model to the right tool moved out of each description's Returns section ([#30](https://github.com/HacksterT/oig-mcp/pull/30)) | A review found FastMCP drops that section before sending a description, so the hints never reached the model |
| Image files are made readable whatever the build machine's permissions ([#33](https://github.com/HacksterT/oig-mcp/pull/33)) | The image built on IBM's virtual machine could not import the server |
| The Orchestrate toolkit passes the data API's settings through a key_value connection ([#35](https://github.com/HacksterT/oig-mcp/pull/35)) | The first registration ran the server with no data API address |
| Facility lookup retries without generic words; state filters accept postal codes; place questions route to the facility tool ([#37](https://github.com/HacksterT/oig-mcp/pull/37)) | The "New York VA" failure in Orchestrate |

The data service fixed backend defects the evaluation found as well, including missing inspections that put one facility's next-window estimate before its latest report, and page footers and split words in extracted text. Because these changes followed earlier results, later runs are not blind tests of those points.

## Speed

Through the server, against the data API, most tools answer in about 0.1 to 0.3 seconds at the median. The inspection brief, which runs several searches, takes about 2 seconds. These figures come from the Claude run of November 10, in the same container image IBM runs, and from small samples. In Orchestrate the server runs over stdio and starts afresh for each call; starting it took about two seconds in a test on the Mac. Of the 5.8-second response measured for the New York question, the data API's part was about 0.16 seconds, and the rest was Orchestrate's model and the process start. The service has not been load tested.

## Security

Every authentication check passed on the Mac, through a public HTTPS tunnel, and on IBM's virtual machine, where the image built there passed all 15 image checks, including the 22 deployment checks run against it. The server refuses to start without a bearer token, with one under 32 characters, or with a plain-HTTP remote data address. With wrong data API credentials it starts, and its tools return a short refusal that does not reveal the API's address. No secret appeared in tool responses, logs, or the image. The run from IBM's virtual machine also confirmed that IBM's network reaches the data API through Cloudflare with no proxy.
