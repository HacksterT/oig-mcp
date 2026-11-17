# Evaluation harness

An assistant answers gold questions using only this server's tools, and its answers are scored against answers computed by SQL. How the testing works is in [`docs/testing-architecture.md`](../docs/testing-architecture.md), and the results are in [`docs/testing-results.md`](../docs/testing-results.md). The same questions run against watsonx Orchestrate's agent as described in [`orchestrate/README.md`](orchestrate/README.md).

## Run it

You need a running server, its bearer token, and an Anthropic API key. In `.env`, or the environment:

```bash
MCP_AUTH_TOKEN=...
ANTHROPIC_API_KEY=...
```

```bash
uv sync --group eval
docker compose up -d --build     # the server, at http://127.0.0.1:8000
uv run --group eval python eval/phoenix/run_experiment.py --url http://127.0.0.1:8000
```

This starts a local Arize Phoenix if none is running, asks all the questions, scores them, and writes `records.json` and `summary.md` under `eval/results/`. A full run took under five minutes and cost about $1.30 to $2.90 at list prices. Add `--keep-phoenix` to browse traces at http://127.0.0.1:6006 afterward.

The harness stops if the server's data differs from the pinned snapshot, because the gold answers would not apply.

| Option | Default | Purpose |
|---|---|---|
| `--url` | `http://127.0.0.1:8000` | Server to test, including a deployed one |
| `--model` | `AGENT_MODEL`, or `claude-opus-5-5` | Assistant under test. A watsonx.ai model ID, such as `meta-llama/llama-3-3-70b-instruct`, runs on IBM watsonx.ai (below) |
| `--judge-model` | `JUDGE_MODEL`, or `claude-opus-5-5` | Model that scores caveats and behaviors |
| `--effort` | `AGENT_EFFORT`, or `medium` | Assistant's effort level |
| `--only` | all | Comma-separated question IDs |
| `--rescore` | | Score a saved results folder again, without asking the assistant |
| `--no-phoenix` | | Skip Phoenix |

## On IBM watsonx.ai models

IBM's `mcp-eval-wxai` skill runs this kind of evaluation with the agent on watsonx.ai. The harness does the same when `--model` is a watsonx.ai model ID: the agent's turns go to IBM's chat API, at temperature 0, with the server's own instructions and tools, and everything else (the questions, the code checks, the Claude judge, Phoenix) is unchanged. A Claude judge on a Llama agent also keeps the judge independent of the agent's model family.

Add the skill's three values to `.env`: `WATSONX_URL` (the region's endpoint, such as `https://ca-tor.ml.cloud.ibm.com`), `WATSONX_API_KEY`, and `WATSONX_PROJECT_ID` (a project with a watsonx.ai Runtime instance). Then check the model, and run:

```bash
uv run --group eval python eval/phoenix/watsonx_smoke.py --model meta-llama/llama-3-3-70b-instruct
uv run --group eval python eval/phoenix/run_experiment.py --url http://127.0.0.1:8000 \
  --model meta-llama/llama-3-3-70b-instruct
```

The smoke test confirms the credentials, that the model is listed for tool calling in the region, a chat call, and a real tool call, and prints no credential. watsonx.ai usage is not priced in the summary.

## Layout

| Path | Contents |
|---|---|
| `gold/build_gold.py` | Computes answers by SQL from the pinned snapshot, opened read-only |
| `gold/questions.json` | The questions, answers, patterns, required tools, and criteria |
| `gold/report_index.json` | Every report number and link in the snapshot, for citation checks |
| `phoenix/agent.py` | The assistant loop, for Claude or a watsonx.ai model, connected to the server over authenticated HTTP |
| `phoenix/watsonx.py` | The watsonx.ai chat client, with IAM token refresh |
| `phoenix/watsonx_smoke.py` | Checks watsonx.ai credentials and tool calling before a run |
| `phoenix/scoring.py` | Scoring by code, and the judge |
| `phoenix/run_experiment.py` | The command above |
| `phoenix/score_external.py` | Scores answers from an agent outside this harness |
| `results/` | Final runs, and earlier runs under `superseded-d364ff4c/` |

## Rebuild the gold answers

The snapshot comes from the `oig-data-source` repository and is too large to keep here. If it changes, update `PINNED_SHA256` in `build_gold.py`, and then:

```bash
python3 eval/gold/build_gold.py --snapshot <folder with oig-<date>.sqlite>
```

## Design choices

**The system prompt is the server's own `instructions`,** so the scores reflect what the server communicates, not a prompt written for this test.

**No refusal fallback.** Anthropic's API can retry a refused request on another model. It is left off here, so each score belongs to the named model. A refusal would be recorded as the answer's stop reason. None occurred.

**Results are computed first, then recorded in Phoenix,** so a Phoenix failure cannot lose a paid run.
