[Wiki](../../README.md) › Evaluation › Debrief

# Debrief: did the changes help?

*A closing assessment of the evaluation, written November 17, 2026, after the final rounds. Every figure comes from [`eval/results/`](../../eval/results/) and can be recomputed with [`eval/verify_scores.py`](../../eval/verify_scores.py). Method: [Method](method.md). Full results: [Results](results.md).*

## Bottom line

Yes. On the agent that had room to improve, the gains were modest and consistent across three independent measures. In reliability and abuse resistance they were large and unambiguous. On Claude they were neutral by design: it was already at the ceiling, so its reruns show that nothing broke. The largest effect in the project remains the server itself: without it, models answer 2 or 3 of 24 questions; with it, 9 to 23.

## Where the changes clearly helped

**The Orchestrate agent (GPT-OSS 120B)** is the cleanest test: the same agent, instruction, and model, with only the server changed.

| 24 main questions | Round 1, three runs | Round 2, two runs | Change |
|---|---|---|---|
| Passing every check | 10, 8, 11 (mean 9.7) | 12, 12 | about +2.3 questions |
| Agrees with the gold reference (judge) | 16, 14, 15 (mean 15) | 19, 19 | +4 |
| IBM's journey success | 14, 14, 13 | 16, 18 | about +3.5 |

Three things make the improvement credible rather than chance:

1. **Every round-2 run beat every round-1 run on all three measures.** Round 1 varied by three questions between runs; both round-2 runs sit above its best.
2. **Four independent scorers moved together:** the code checks, the Claude judge, IBM's evaluation engine, and Phoenix's correctness judge on watsonx.ai, built as IBM's skill specifies (16, 16, and 15 of 24 correct in round 1; 20 and 20 in round 2).
3. **The gains fall on the questions the fixes targeted.** The peak year (now precomputed by the server), the VBA median, and the no-forecast question failed every round-1 run and passed both round-2 runs.

**Reliability and abuse resistance:**

- A burst of 45 calls on protocol 2026-07-28 went from 0 answered to 29, after the rate-limit fix.
- Under load, 2,059 of 2,059 calls were answered at 40 concurrent clients.
- The robustness check grew from 43 to 49 hostile inputs, all passing.
- On the adversarial set, Claude Opus went from 5 to 6 of 6 and Llama 3.3 70B from 0 to 4 of 6.

**Ambiguous facility names in real hosts:** before the change in [#92](https://github.com/HacksterT/oig-mcp/pull/92), Hermes Agent and Claude Desktop each chose a facility for "the New York VA"; after it, both asked the user. That is one trial per host: a strong example, not a measurement.

## Where the changes did not help, or the effect is unknown

- **Which tool the agent chose, and with which arguments, did not move:** Phoenix's tool selection and tool invocation judges scored Orchestrate about the same in both rounds. The server improved what the agent did with results, not its choice of tool.
- **Links in GPT-OSS answers barely moved,** 3 of 8 at best in both rounds. A ready-made citation helps a model that copies it (Claude Sonnet reached 8 of 8), not one that omits links.
- **Five questions regressed** from passing once in round 1 to failing both round-2 runs. Three of them met Orchestrate's own "connection refused" tool errors in round 2's first run; the other two look like sampling variance, which two runs cannot settle.
- **The Orchestrate agent failed the instruction-override question** in both adversarial runs.
- **Llama 3.3 70B stayed at 9 of 24.** Its tool choice, citations, and data dates improved, and the cause of its context overflow was found and the page cut by 42 percent, but Llama was not rerun, so a fix there is unproven.
- **The last three server changes** ([#101](https://github.com/HacksterT/oig-mcp/pull/101) to [#103](https://github.com/HacksterT/oig-mcp/pull/103)) are unmeasured on weaker models: Orchestrate's round 2 ran the earlier code. Claude Sonnet shows they broke nothing.
- **The server-side facility form** (MCP elicitation) is proven end to end only with the MCP SDK's client; the desktop hosts tried did not display it.

## What the Phoenix evaluators showed

The Phoenix evaluation was a second, independent grading of the saved answers, with nothing rerun. Llama 3.3 70B on watsonx.ai read each answer with the tool calls behind it and gave five verdicts, as IBM's `mcp-eval-wxai` skill specifies: correctness against the SQL-computed reference, scope, tool selection, tool arguments, and whether the answer used its tool responses faithfully. Full tables: [Results](results.md#phoenix-evaluators-on-watsonxai).

1. **It confirms the main result with a judge this project did not build.** With only the server changed, Orchestrate's correct answers rose from 16, 16, and 15 of 24 to 20 and 20, the same jump the Claude judge found (about 15 to 19). Two judges from different model families agreeing makes the improvement much harder to dismiss.
2. **The improvement came from how the agent used results, not which tool it chose.** Orchestrate's tool selection (15, 13, 14 to 14, 16) and tool arguments (16, 19, 17 to 19, 17) did not move. The server's changes worked by making results clearer and harder to misread, such as a precomputed peak year, wrong filters refused with the fix, and ready-made citations, not by improving the agent's choice of tool.
3. **Claude is close to perfect on what matters:** correct on 30 of 30 (Opus) and 29 of 30 (Sonnet), in scope every time, and faithful to its tool responses in all 26 answers that called tools.
4. **Claude's low tool selection score is the judge disagreeing with the server's design, not a failure.** Phoenix scored it 7 and 11 of 30 because of two correct behaviors: calling the dataset status tool first, which the server instructs and five questions require, and refusing questions such as "Which VA facility is the worst?" without calling a tool. These account for every Opus failure and 18 of Sonnet's 19. Llama and Orchestrate also had 6 to 9 genuine wrong-tool choices per run.
5. **The weaker agents' real problems showed clearly.** The remaining response handling failures are genuine: answers that ignored a tool error, or misread which open recommendation was oldest in a long result. Llama was correct on 15 of 24, in line with the other measures.

**On method:** a first pass judged response handling one tool call at a time, so when an answer combined two calls (Texas from one, North Carolina from the other), each call made the other half look invented. Judged with all of an answer's calls together, the way the agent saw them, those false failures disappeared. Both passes are recorded.

**In one line:** an independent judge, built as IBM intended, confirms that the server's changes made a weaker agent noticeably more accurate, about 16 to 20 of 24, mainly by helping it use results correctly rather than choose tools better, while Claude stayed near perfect throughout.

## How much weight the evidence bears

- **Not blind.** One person wrote the questions and the fixes, and round 2 retested the questions that drove the fixes. Round 2 shows the fixes work on those questions, not that they generalize.
- **Small numbers.** Twenty-four questions and two or three runs establish a direction, not statistical significance.
- **Judges.** The Claude judge did most of the judging. The watsonx.ai judge agreed with it on 89 of 90 answers, and IBM's engine moved the same way.
- **A strict scorer, applied consistently.** "Agreed" for "concur", and a typographic quote attached to a real link, both count as failures. The scorer was never loosened after seeing a result.

## What the evidence supports claiming

**Supported:** changing only the server raised a fixed agent from 10 or 11 to 12 of 24 questions, and its judged agreement from about 15 to 19 of 24, measured three ways; the server lifts models from 2 or 3 of 24 to between 9 and 23; it answered every call under load and passes every hostile-input check.

**Not supported:** statistical significance, a blind test, generalization to new questions, or the elicitation form working in a desktop host.

## What we would do differently

- **A separate folder for every test round,** from the start. A shared folder caused a wrong first score for round 2, caught because it matched round 1 exactly.
- **A real third-party client before calling a server change done.** The HTTP session regression appeared within an hour of every automated check passing.
- **A small held-out question set, written before any fixes.** It is the one addition that would turn "improved on the questions we fixed" into "improved."

---

← [Results](../evaluation/results.md) · [Wiki home](../../README.md)
