# Note 14: rerun the questions on the final server

Claude scored your three runs against the gold. The failures led to server fixes now on main, frozen at tag `eval-final-1`. The test set is 30: the same 24, plus six adversarial questions numbered 25 to 30. Orchestrate's toolkit still runs the old server code until it is imported again. Claude's own runs are finished, so nothing else is using the data API while you run. Do these steps in order.

## How we talk during this note

You and Claude work through the repository, not through Troy.

- **Status, after every step.** Add one line to `docs/handoff/Bob-communication/bob-status.md` on `ibm/deploy`, commit, and push: `<UTC time> | step <n> | done, waiting, or blocked | <one line>`. Claude watches `ibm/deploy` and reads each push.
- **A question for Claude.** Write the question on a status line starting `QUESTION:`, push, and stop. Then run `git pull --no-rebase origin main` every 5 minutes and look for `docs/handoff/Bob-communication/reply14-<n>.md`. Claude's reply wins over this note. If no reply arrives within an hour, tell Troy.
- **Something only Troy can do.** The Orchestrate interface and its chat are Troy's. Ask him directly in your session, say exactly what to do and what to send back, and record "waiting on Troy" in the status file until he answers.
- The repository is public: the status file and replies follow the same privacy rules as your report.

## 1. Update and re-import the toolkit

```bash
git checkout ibm/deploy
git pull --no-rebase origin main
bash deploy/ibm/local-mcp-toolkit/register-toolkit.sh
```

The script replaces the toolkit. Then ask **Troy** to open `gsa-oig-assist-TES` in the Orchestrate UI and add the seven `oig_mcp_TES` tools back. Nothing else about the agent changes: not its instruction, its model (gpt-oss-120b), or anything else.

## 2. Check it took effect

Ask **Troy** to ask the agent in a new chat: "How many open recommendations does the Office of Information and Technology have?" The answer should be **57**. If it says none, the old toolkit is still in place: record it as blocked and stop.

## 2b. Check how the agent handles an ambiguous facility name

Ask **Troy** to ask these two questions in a new chat, one at a time, and to tell you what appeared for each:

1. "What has OIG found at the New York VA?"
2. "What has OIG found at the California VA?"

Each name matches several facilities. For each question, record which of these happened:

- **A form with a list of facilities.** Orchestrate supports MCP elicitation. Troy picks one; record whether the answer covered that facility only.
- **No form, and the agent listed the facilities and asked which one.** The server's instruction worked.
- **The agent chose a facility itself and answered for it.** Record which facility.

If Troy takes a screenshot, it is saved outside the repository and never committed. Either way, carry on to step 3.

## 3. Rebuild the tests for the agent's internal name

```bash
uv run python eval/orchestrate/build_tests.py --agent <internal agent name>
```

Do not commit the test files with the internal name in them: run `git checkout -- eval/orchestrate/tests` before you commit.

## 4. Run all 30, twice

Run `orchestrate env activate gsa-hackathon` again **immediately before each run**: run 1 last time hit "token has expired" twice. Write the runs to `eval/results/<UTC date>-orchestrate/run-1` and `run-2`, the same layout as last time. Two runs, not three: the three earlier runs already measured how much the agent varies from run to run.

## 5. Scrub, then push to ibm/deploy

- Delete each run's `debug/` folder.
- In each `config.yml`, replace the token with `REDACTED`, and replace the instance URL with `https://api.REGION.watson-orchestrate.cloud.ibm.com/instances/REDACTED`.
- Replace `/home/<user>/` paths with `~/`.
- Search the results for the instance ID, the internal agent name, and internal IP addresses, and redact any you find.

## 6. The demo recording (Troy's)

After the runs are pushed, ask **Troy** to record one short screen recording for the presentation deck, and give him this list. He starts a new chat in `gsa-oig-assist-TES` and asks these six questions in order, waiting for each answer to finish:

1. "How current is the data?"
2. "Which offices have the most recommendations open longer than a year?"
3. "What did facilities commit to doing about unsecured medication carts?"
4. "Prepare an inspection brief for the Durham VA Medical Center."
5. "What has OIG found at the New York VA?" If the agent asks which facility, answer "the Bronx".
6. "Which VA facility is the worst?"

The recording shows only the chat area, with nothing private visible: no address bar, instance URL or ID, account name or email, or internal agent name. It is not committed. Record in your report where Troy says it is and anything he says went wrong; do not retry for a better take.

## 7. Report

Write `docs/handoff/<UTC date>-bob-orchestrate-rerun.md` with only these sections:

1. **Setup:** the toolkit import time (UTC), confirmation that the tools were re-added, the step 2 answer, and the ADK and judge versions.
2. **Ambiguous names:** what appeared for each step 2b question.
3. **Runs:** one row per run with start, end, tests completed, and tests that errored.
4. **Errors:** every tool error, with run, test, approximate UTC time, and the exact message.
5. **Privacy check:** what you searched for and what you redacted.
6. **Recording:** where Troy saved it, its length, and anything he noted.

Do not copy the answers or the per-test tables; Claude reads them from the result files. Push, add a final status line `step 7 | done`, and tell Troy it is done.
