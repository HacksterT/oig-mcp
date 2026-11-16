# Evaluation

oig-mcp is tested in layers, from automated tests on every change to an AI agent answering 24 gold questions using only the server's tools, on three platforms: Claude, DeepSeek through Hermes Agent, and IBM's own agent in watsonx Orchestrate.

- [**Testing architecture**](testing-architecture.md): what is tested and why, the evaluation harness and how it maps to IBM's `mcp-eval-wxai` method, how answers are scored, and the limits.
- [**Testing results**](testing-results.md): the scores on each platform with their limits, what testing changed, speed, and security.

To run the evaluation, see [`eval/README.md`](../eval/README.md) and [`eval/orchestrate/README.md`](../eval/orchestrate/README.md).
