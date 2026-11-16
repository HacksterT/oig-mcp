# Note 10: Orchestrate evaluation — staged and ready to run

**Written by Bob on 2026-11-16.**

This note documents the ADK evaluation access and what is ready to run when Troy gives the go-ahead (per note 8).

---

## What is available

The `orchestrate evaluations evaluate` command is available on this VM via ADK 2.20.0. It can run the 24 JSON test cases in `eval/orchestrate/tests/` directly against the live `gsa-oig-assist-TES` agent in the `gsa-hackathon` environment.

Command shape (do not run until Troy says so):
```bash
orchestrate evaluations evaluate \
  --config eval/orchestrate/config.yaml \
  --test-paths eval/orchestrate/tests/ \
  --output-dir eval/orchestrate/results/
```

The ADK environment `gsa-hackathon` is active and authenticated. The token expires; re-activate with `IBM_API_KEY` from `.env` if needed:
```bash
WXO_KEY="$(grep -E '^IBM_API_KEY=' .env | tail -1 | cut -d= -f2- | tr -d "\"'")"
orchestrate env activate gsa-hackathon --api-key "$WXO_KEY"
```

---

## What needs to be done before running

1. **Fill in `eval/orchestrate/config.yaml`** from `eval/orchestrate/config.example.yaml` — needs the agent name (`gsa-oig-assist-TES`) and any judge settings. Do not commit it (it may contain the agent name or other run-specific values; check `.gitignore`).
2. **Finish note 7** — Q5 retest answer must be pasted back and the Phases 2–4 report updated and pushed before the evaluation runs.
3. **Wait for Troy's go-ahead** per note 8: do not run while Troy's UI evaluation is in progress.

---

## Other eval subcommands available

| Command | Purpose |
|---|---|
| `orchestrate evaluations evaluate` | Run test cases against a live agent |
| `orchestrate evaluations record` | Record chat sessions and create test cases |
| `orchestrate evaluations generate` | Generate test cases from user stories and tools |
| `orchestrate evaluations analyze` | Analyze results of a previous run |
| `orchestrate evaluations quick-eval` | Static metrics + LLM-as-judge |
| `orchestrate evaluations validate-native` | Validate native agents against inputs |

---

## Orchestrate test case format

A sample test case in the UI's JSON format is at `docs/handoff/Bob-communication/q01-test.json` (pushed to `ibm/deploy`). Instance-specific fields (`id`, `agent_id`, `created_by`, `updated_by`, `dataset_name`) were stripped before committing — they contain private values not suitable for a public repo. The remaining structure shows Claude exactly what format to use when generating the remaining 23 test cases.

The template endpoint `GET /v1/orchestrate/agent/test_case/templates` returned 404 on this instance — the sample JSON is the only format reference available.

## Current hold

Per note 8: do not re-register the toolkit, change the agent, or run the evaluation until Troy sends a note saying to proceed. The agent `gsa-oig-assist-TES` is steady with 7 tools from `oig_mcp_TES`.
