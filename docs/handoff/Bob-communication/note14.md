# Note 14: rerun the questions on the updated server

Claude scored your three runs against the gold. The failures led to server fixes now on main, and a data API fix that is already live. The test set is now 30: the same 24, plus six adversarial questions numbered 25 to 30 (an instruction to break the rules, injected text, a report that does not exist, a medical emergency, a request to name employees, and an out-of-domain question). Orchestrate's toolkit still runs the old server code until it is imported again. Do these steps in order. Claude runs nothing against the data API while you run.

## 1. Update and re-import the toolkit

```bash
git checkout ibm/deploy
git pull origin main
bash deploy/ibm/local-mcp-toolkit/register-toolkit.sh
```

The script replaces the toolkit. Then **Troy** opens `gsa-oig-assist-TES` in the Orchestrate UI and adds the seven `oig_mcp_TES` tools back. Do not change the agent's instruction, model (gpt-oss-120b), or anything else.

## 2. Check it took effect

Ask the agent in chat: "How many open recommendations does the Office of Information and Technology have?" The answer should be **57**. If it says none, the old toolkit is still in place: stop and report.

## 3. Rebuild the tests for the agent's internal name

```bash
uv run python eval/orchestrate/build_tests.py --agent <internal agent name>
```

Do not commit the test files with the internal name in them: run `git checkout -- eval/orchestrate/tests` before you commit.

## 4. Run all 30, three times

Run `orchestrate env activate gsa-hackathon` again **immediately before each run**. Run 1 last time hit "token has expired" twice. Write the runs to `eval/results/<UTC date>-orchestrate/run-1`, `run-2` and `run-3`, the same layout as last time.

## 5. Scrub, then push to ibm/deploy

- Delete each run's `debug/` folder.
- In each `config.yml`, replace the token with `REDACTED`, and replace the instance URL with `https://api.REGION.watson-orchestrate.cloud.ibm.com/instances/REDACTED`.
- Replace `/home/<user>/` paths with `~/`.
- Search the results for the instance ID, the internal agent name, and internal IP addresses, and redact any you find.

## 6. Record the demo

After the three runs are pushed, record one short screen recording of the agent for the presentation deck. Start a new chat in `gsa-oig-assist-TES` and ask these five questions in order, waiting for each answer to finish:

1. "How current is the data?"
2. "Which offices have the most recommendations open longer than a year?"
3. "What did facilities commit to doing about unsecured medication carts?"
4. "Prepare an inspection brief for the Durham VA Medical Center."
5. "Which VA facility is the worst?"

- Record only the chat area, at a readable size, with the full answers visible. Scroll slowly through long answers. Aim for under four minutes in total.
- Nothing private may be visible: no browser address bar, instance URL or ID, account name or email, the internal agent name, or anything outside Orchestrate's chat. Check the whole recording before you hand it over, and record again rather than editing out a leak.
- Do not commit the recording. Save it outside the repository and tell Troy where it is.
- If a question gets an error or a wrong answer, keep going and note it. Do not retry to get a better take.
- If you cannot record the screen from the VM, say so in the report, and Troy will record it himself.

## 7. Report

Write `docs/handoff/<UTC date>-bob-orchestrate-rerun.md` with only these sections:

1. **Setup:** the toolkit import time (UTC), confirmation that the tools were re-added and the step 2 answer, and the ADK and judge versions.
2. **Runs:** one row per run with start, end, tests completed, and tests that errored.
3. **Errors:** every tool error, with run, test, approximate UTC time, and the exact message.
4. **Privacy check:** what you searched for and what you redacted.
5. **Recording:** where it is saved, its length, and any question that got an error or an answer you think is wrong.

Do not copy the answers or the per-test tables; Claude reads them from the result files. Push, then tell Troy it is done.
