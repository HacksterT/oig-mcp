# Note 15: Bob's handoff to Claude — where everything is

This note is from Bob (the VM) to Claude (on Troy's Mac). It is a map of what was done in note 14 and where the results sit, so Claude can score the runs and write the final assessment without asking questions.

---

## What note 14 asked for

Re-import the toolkit with the fixed server code (tagged `eval-final-1` on main), re-add the tools to the agent, verify the fix, and run all 30 questions twice against the live Orchestrate agent. The 30 questions are the original 24 gold questions plus 6 adversarial questions numbered 25–30.

---

## What was done and where the results are

### Toolkit and agent (steps 1–2b)

- Toolkit `oig_mcp_TES` was removed and re-imported from the current `main` codebase at **2026-11-17T17:51:41Z**.
- Troy re-added all 7 tools to `gsa-oig-assist-TES` in the Orchestrate UI.
- Verification question answered correctly: OIT open recommendations = **57**.
- Ambiguous facility name results are in **section 2** of `docs/handoff/2026-11-17-bob-orchestrate-rerun.md`.

### Test files

- `eval/orchestrate/tests/` — 30 JSON test files, `agent` field set to display name `gsa-oig-assist-TES` (scrubbed; internal name was `the internal agent name`, used only during runs).
- Tests 01–24 are the original gold questions. Tests 25–30 are adversarial.

### Run results

Both runs are in `eval/results/2026-11-17-orchestrate/`:

```
run-1/   — started ~2026-11-17T18:06:45Z, 30 tests completed
run-2/   — started ~2026-11-17T18:39:03Z, 30 tests completed
```

Each run folder contains:
- `messages/<test>.messages.json` — full conversation transcript (tool calls, tool responses, agent replies, simulated-user turns)
- `messages/<test>.messages.analyze.json` — ADK's per-turn annotation
- `messages/<test>.metrics.json` — ADK's per-test scores
- `<test>.metadata.json` — test-level metadata
- `average_metrics.json` — run-level averages
- `summary_metrics.csv` — one row per test
- `config.yml` — run configuration (token and instance URL redacted)

The ADK also writes a dated subfolder (`2026-11-17_18-06-45/` etc.) with the same files. Both copies are present.

**Note on adversarial tests:** The ADK's parallel worker pool dropped tests 25–30 during the main batch (connection-refused on the tool executor mid-batch). They were re-run immediately in a separate 6-test batch per run and merged. The message and metrics files for all 30 tests are present in both runs.

### Tool errors recorded

Three `connection refused` errors occurred in run-1 (tests `closure-vha-rate`, `trend-suicide`, `count-two-states`). None recurred in run-2. See **section 4** of the rerun report for the exact messages.

### Privacy scrub

- `debug/` folders deleted from both runs.
- Instance ID, instance URL, and auth token redacted in all files.
- Internal agent name restored to display name in test files.
- Home path (`/home/<user>/`) replaced with `~/` in config files.
- Final grep confirmed 0 hits for any sensitive value in run-1 and run-2.

---

## Files Claude should read

| File | What it contains |
|---|---|
| `docs/handoff/2026-11-17-bob-orchestrate-rerun.md` | Full rerun report: setup, ambiguous-name results, run table, error log, privacy check |
| `eval/results/2026-11-17-orchestrate-round-2/run-1/messages/` | Run-1 transcripts and per-test metrics (30 tests) |
| `eval/results/2026-11-17-orchestrate-round-2/run-2/messages/` | Run-2 transcripts and per-test metrics (30 tests) |
| `eval/results/2026-11-17-orchestrate-round-2/run-1/average_metrics.json` | Run-1 aggregate scores |
| `eval/results/2026-11-17-orchestrate-round-2/run-2/average_metrics.json` | Run-2 aggregate scores |
| `eval/gold/questions.json` | The 30 gold questions with reference answers and expected tools |
| `docs/handoff/2026-11-17-bob-orchestrate-evaluation.md` | Earlier evaluation report (runs 1–3 on the old server code) for comparison |

---

## What Claude still needs to do

Per note 14 step 7, Claude scores the runs from the result files. Bob's report intentionally contains no per-test scores or answer tables — those come from Claude's own scoring pass.

The demo recording (note 14 step 6) was not done today. Troy will record it before the presentation. When he does, Bob will add a note here.

---

## Branch and commit

All results are on `ibm/deploy`, commit `f1db57b` ("note14 step 7: rerun report + final status, all steps done"). `main` is unchanged.
