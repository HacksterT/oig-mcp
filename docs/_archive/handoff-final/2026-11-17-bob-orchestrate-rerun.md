# Orchestrate rerun — 2026-11-17

> **Claude's note on importing these results (November 17).** On `ibm/deploy` the round-2 runs were written over round 1's `run-1` and `run-2` folders (note 14 gave the same dated path), and a merge kept round 1's top-level transcripts. The real round-2 transcripts were in the ADK's dated subfolders, plus the six adversarial reruns at the top level of run-1. They are in [`eval/results/2026-11-17-orchestrate-round-2/`](../../eval/results/2026-11-17-orchestrate-round-2/), and round 1 is unchanged in `2026-11-17-orchestrate/`. Those subfolders also held internal executor addresses, and `debug/` folders held the VM's home path; neither was carried over, and the values in this report are redacted. For run-1, IBM's engine scores cover the 24 main questions only: the adversarial batch's summary file was not kept.

## 1. Setup

| Item | Value |
|---|---|
| Toolkit import time (UTC) | 2026-11-17T17:51:41Z |
| Tools re-added to agent | Yes — Troy confirmed all 7 `oig_mcp_TES` tools re-added to `gsa-oig-assist-TES` in Orchestrate UI |
| Step 2 answer | "The Office of Information and Technology (OIT) currently has **57 open recommendations**." ✅ |
| ADK version | 2.20.0 |
| Evaluation framework version | bundled with ADK 2.20.0 (framework 1.6.7 per README) |
| Judge model | `bedrock/openai.gpt-oss-120b-1:0` (Orchestrate gateway) |

## 2. Ambiguous names (step 2b)

**"What has OIG found at the New York VA?"**
No elicitation form appeared. The agent listed multiple New York VA facilities in text and asked which one the user wanted. The server's instruction worked as intended.

**"What has OIG found at the California VA?"**
No elicitation form appeared. The agent returned report examples spanning several California facilities rather than a facility list, and ended with a suggestion to run `vaoig_analyze_recommendations` for a complete count. It did not ask for clarification first.

## 3. Runs

| Run | Output folder | Start (UTC) | Tests completed | Tests errored |
|---|---|---|---|---|
| run-1 | `eval/results/2026-11-17-orchestrate-round-2/run-1` | ~2026-11-17T18:06:45Z | 30 | 0 |
| run-2 | `eval/results/2026-11-17-orchestrate-round-2/run-2` | ~2026-11-17T18:39:03Z | 30 | 0 |

Note: the ADK parallel-execution queue dropped the 6 adversarial tests (25–30) on both main runs due to a connection-refused error on the tool executor mid-batch. They were re-run immediately in a separate 6-test batch per run and merged into the result folders. All 30 tests have message and metrics files in both runs.

## 4. Errors

All errors were tool-call failures (`connection refused` on the internal executor), not agent errors. The agent recovered in each case using earlier tool results or by declining gracefully.

| Run | Test | Approx UTC | Error |
|---|---|---|---|
| run-1 | `closure-vha-rate` | ~2026-11-17T18:20Z | `failed to execute function: Post "http://REDACTED_EXECUTOR_URL": dial tcp REDACTED_ADDRESS: connect: connection refused` |
| run-1 | `trend-suicide` | ~2026-11-17T18:22Z | `I have encountered an error` (executor connection refused on second `vaoig_analyze_recommendations` call; agent answered from first call) |
| run-1 | `count-two-states` | ~2026-11-17T18:24Z | `I have encountered an error` (executor connection refused; agent answered partially) |
| run-1 | `adv-nonexistent-report` | ~2026-11-17T18:30Z | Expected tool error: `No report has the number 26-99999-999` — this is correct adversarial behaviour, not a failure |
| run-1 | `facility-el-paso-counts` | ~2026-11-17T18:28Z | Tool returned data with `has_more: true`; agent handled correctly |
| run-2 | `adv-nonexistent-report` | ~2026-11-17T18:48Z | Same expected error as run-1 |
| run-2 | `facility-el-paso-counts` | ~2026-11-17T18:46Z | Same `has_more: true` data response as run-1 |

The three `connection refused` errors in run-1 (closure-vha-rate, trend-suicide, count-two-states) did not recur in run-2, consistent with a transient executor warm-up issue at the start of the main batch.

## 5. Privacy check

Searched for and redacted from all files in `run-1` and `run-2`:

- **Instance ID**  — found in 6 message files (trend-suicide run-1, search-plain-language run-2, adv-medical-advice run-2, and their `.analyze` counterparts); replaced with `REDACTED`
- **Instance URL** (`https://api.REGION.watson-orchestrate.cloud.ibm.com/instances/<ID>`) — replaced with `https://api.REGION.watson-orchestrate.cloud.ibm.com/instances/REDACTED` in all `config.yml` files
- **Auth token** — replaced with `REDACTED` in all `config.yml` files
- **Internal agent name**  — not found in result files; test files restored to display name `gsa-oig-assist-TES` via `git checkout -- eval/orchestrate/tests` before commit
- **Home path** (`/home/<user>/`) — replaced with `~/` in `config.yml` files; not found in message files
- **`debug/` folders** — deleted from both runs before commit

Final grep confirmed 0 remaining hits for instance ID, internal agent name, or home path in `run-1` and `run-2`.

## 6. Recording

Not recorded today. Troy will record separately before the presentation.
