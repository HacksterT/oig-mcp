# Evaluating the Orchestrate agent

**In the Orchestrate UI:** work from [`test-bank.md`](test-bank.md), which follows IBM's field names. Save each question from the preview chat as a test, replace its **Response summary** with the one on the page and turn on its evaluation toggle, set tool parameters to **Ignored**, and add the listed keywords. The page also has four custom LLM-as-a-Judge metrics (IBM scores 1 for pass). Correctness is scored again on the Mac with `eval/phoenix/score_external.py` and the data API's traces.

**From the command line:** the same 24 gold questions the Claude evaluation uses ([`../gold/questions.json`](../gold/questions.json)), written as watsonx Orchestrate test cases in [`tests/`](tests/). Running them scores Orchestrate's own agent and model on the same questions, so the two results can be compared directly.

## Agent under test

`gsa-oig-assist-TES` with the `oig_mcp_TES` toolkit and one instruction, no guidelines:

> Answer only from what the OIG tools return. Do not use general knowledge or information outside the tool results.

It grounds answers in the tools without adding domain logic, which stays in the server. Keep the agent unchanged across runs, and record any change with the results.

## What each test checks

| Goal in the test | Comes from | Judged by |
|---|---|---|
| A call to `oig_mcp_TES:<tool>` | The gold question's required tool, when it names exactly one per step | Journey success, tool call precision and recall |
| Final answer text and keywords | The gold reference answer, and the facts our checks look for (counts, dates, report numbers) | Text match, by an AI judge |
| `assert_llm` checks | The gold criteria (no percentage for missed targets, no ratings, flag an ambiguous facility, label estimates), and citation and data-date rules | An AI judge on the final answer |

Choices to know when reading results:

- **Arguments are not compared** (`{"IGNORE": null}`), because the agent's wording of an argument varies between runs. What the tool returned is judged through the answer.
- **Twelve questions check only the answer.** Their gold questions accept either of two tools (for example the facility profile or the inspection brief), and a test case cannot express "either", or the right answer needs no tool. A missing tool goal there is deliberate.
- **Answers vary between runs.** Run each test more than once before calling a question failed.

## Run

With the ADK installed and the agent's environment active (`orchestrate env activate <name>`), copy the config, fill in the instance URL, and run:

```bash
cp eval/orchestrate/config.example.yaml eval/orchestrate/config.yaml
orchestrate evaluations evaluate --config eval/orchestrate/config.yaml
```

Results go to `eval/orchestrate/results/`, which git ignores: a `*.metrics.json` and an annotated `*.messages.analyze.json` per test. Evaluations run against the agent's draft version.

The judge model defaults to `gpt-oss-120b`; set `EVAL_MODEL` to change it.

## Regenerate

After changing the gold questions, or to target a different agent or toolkit name:

```bash
uv run python eval/orchestrate/build_tests.py --agent gsa-oig-assist-TES --toolkit oig_mcp_TES
```

If the ADK reports that it does not recognize `assert_llm`, its evaluation framework is older: add `--no-assert`.
