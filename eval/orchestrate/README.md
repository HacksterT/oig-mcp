# Evaluating the Orchestrate agent

The same 24 gold questions the Claude evaluation uses ([`../gold/questions.json`](../gold/questions.json)), run against watsonx Orchestrate's own agent and model, so the two results compare directly. Two ways to run them:

- **ADK command (preferred):** [`tests/`](tests/) holds all 24 as test cases. One command runs them all against the live agent, with Orchestrate's own simulated user and judge. Repeatable, and nothing is set up by hand.
- **Orchestrate UI:** [`ui-tests/`](ui-tests/) holds all 24 in the JSON format the UI shows under Modify JSON (modeled on a saved test exported from the instance), for upload through the test case API or pasting into a saved test. [`test-bank.md`](test-bank.md) gives the same settings field by field, and four custom LLM-as-a-Judge metrics.

Either way, correctness is scored again on the Mac with `eval/phoenix/score_external.py` and the data API's traces.

## Agent under test

`gsa-oig-assist-TES` with the `oig_mcp_TES` toolkit and one instruction, no guidelines:

> Answer only from what the OIG tools return. Do not use general knowledge or information outside the tool results.

It grounds answers in the tools without adding domain logic, which stays in the server. Keep the agent unchanged across runs, and record any change with the results.

## What each test checks

| Goal in the test | Comes from | Judged by |
|---|---|---|
| A call to the tool, with its critical argument compared | The gold question's required tool, when it names exactly one per step | Journey success, tool call precision and recall, parameter F1 |
| Final answer text and keywords | The gold reference answer, and the facts our checks look for (counts, dates, report numbers) | Text match, by an AI judge |
| `assert_llm` checks | The gold criteria (no percentage for missed targets, no ratings, flag an ambiguous facility, label estimates), and citation and data-date rules | An AI judge on the final answer |

Choices to know when reading results:

- **Tool names are bare** (`vaoig_get_report`), as Orchestrate records them in a saved test.
- **Only the critical argument is compared:** strict for identifiers and fixed values (a report number, `group_by`, open status), fuzzy for names and free text. Other arguments are ignored, since their wording varies between runs.
- **Twelve questions check only the answer.** Their gold questions accept either of two tools (for example the facility profile or the inspection brief), and a test case cannot express "either", or the right answer needs no tool. A missing tool goal there is deliberate.
- **Answers vary between runs.** Run three times before calling a question failed.

## Run

From the repository root on a machine with the ADK, with the agent's environment active (`orchestrate env activate gsa-hackathon`). No config file is needed: the ADK takes the instance URL and login from the active environment, and a config file with its own `auth_config` would replace that login.

```bash
orchestrate evaluations evaluate \
  --test-paths eval/orchestrate/tests \
  --output-dir eval/orchestrate/results/run-1
```

Repeat as `run-2` and `run-3`. Each run writes a `*.metrics.json` and an annotated `*.messages.analyze.json` per test. Evaluations run against the agent's draft version.

The simulated user and the judge use `gpt-oss-120b` through Orchestrate's own model gateway, with no extra key. Set `EVAL_MODEL` to change it; with `WATSONX_SPACE_ID` and `WATSONX_APIKEY` set, the ADK uses watsonx.ai instead. The ADK on the VM (2.20.0) bundles evaluation framework 1.6.7, which accepts these files.

## Regenerate

After changing the gold questions, or to target a different agent:

```bash
uv run python eval/orchestrate/build_tests.py --agent gsa-oig-assist-TES
```

If the ADK reports that it does not recognize `assert_llm`, its evaluation framework is older: add `--no-assert`.
