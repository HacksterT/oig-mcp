# Note 12: report the evaluation runs directly to Claude

Troy is not relaying results. Write your report of the note 11 runs as a file in the repository, push it to `ibm/deploy`, and Claude reads it from GitHub. Write facts, not interpretation: Claude scores the answers against the gold and settles any disagreement between judges.

Save it as `docs/handoff/<date>-bob-orchestrate-evaluation.md`, using the UTC date of the first run, with these sections in this order.

## 1. Setup

- The agent check from note 11: the tool count, and the instruction text exactly as Orchestrate shows it.
- `orchestrate --version`, and the evaluation framework version if the ADK prints it.
- The judge and simulated-user model and provider the ADK used (`EVAL_MODEL`, or the default it logged).
- Anything you set, changed, or installed for the run.

## 2. Runs

A table with one row per run: run name, UTC start, UTC end, tests completed out of 24, and any test that errored instead of completing.

## 3. Summary per run

For each run, the summary table the ADK prints, copied exactly.

## 4. Results per test

One table per run, one row per test: test name, journey success, journey completion, tool call precision, tool call recall, text match, keywords (pass or fail), `assert_llm` checks passed out of total, number of tool calls, and response time.

## 5. Failures

For every test that failed any check in any run: which check, the judge's stated reasoning copied from the results, the tools the agent called (with the critical argument's value), and the agent's final answer copied exactly. Group by test, so a test that failed in two runs shows both.

## 6. Answers

The agent's final answer to every test in run 1, copied exactly, under a heading per test (`### 01 count-open-total` and so on). Runs 2 and 3 are in the results folders.

## 7. Errors and anything unexpected

Exact error text, retries, token expiry, slow tests, a test where the simulated user asked something odd. Say "none" if there were none.

## 8. Privacy check

What you searched the results for (instance URL or ID, agent ID, email addresses, tokens), what you found, and what you removed, file by file. Say so if you removed nothing.

## When done

Commit the report together with the three results folders from note 11, push to `ibm/deploy`, and tell Troy in one line that the report is pushed. That line is all Troy needs to pass on.
