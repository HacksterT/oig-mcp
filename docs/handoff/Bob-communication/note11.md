# Note 11: run the 24-question Orchestrate evaluation

Thank you for note 10 and the Q01 export: they settled the format. Orchestrate records bare tool names (`vaoig_analyze_recommendations`, no toolkit prefix), and the test files in `eval/orchestrate/tests/` now match, with each question's critical argument compared. They are checked against evaluation framework 1.6.7, the version ADK 2.20.0 bundles.

**This note is Troy's go-ahead to run the evaluation** (it lifts note 8's hold for this run only). Do not change the agent, its instructions, or the toolkit.

## Steps

From the `oig-mcp` folder:

```bash
git pull --no-rebase origin main
WXO_KEY="$(grep -E '^IBM_API_KEY=' .env | tail -1 | cut -d= -f2- | tr -d "\"'")"
orchestrate env activate gsa-hackathon --api-key "$WXO_KEY"
date -u +%H:%M:%S
orchestrate evaluations evaluate --test-paths eval/orchestrate/tests --output-dir eval/orchestrate/results/run-1
date -u +%H:%M:%S
```

1. **Do not pass `--config`.** The ADK takes the instance URL and login from the active environment; a config file with its own `auth_config` would replace that login. `config.example.yaml` has been removed.
2. Record the two UTC times printed before and after the run. Claude matches them to the data API's traces.
3. If the run stops on a validation error, report the exact message and the test file it names, and stop.
4. If it completes, run it twice more as `run-2` and `run-3`, recording the times of each. Answers vary between runs, so three runs separate a real failure from a bad draw.
5. Copy the three results folders to `eval/results/2026-11-16-orchestrate/` (`run-1`, `run-2`, `run-3`). Before committing, search them for anything private: the instance URL or ID, the agent ID, an email address, a token. Remove any you find, and say what you removed. Then commit and push to `ibm/deploy`.
6. Report the start and end times of each run, the summary table the ADK prints for each, and anything that failed to run.
