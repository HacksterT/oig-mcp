# Note 8: the Orchestrate evaluation, and what it means for you

Troy is evaluating the Orchestrate agent with the same 24 gold questions used for Claude. He builds the test bank in the Orchestrate UI from [`eval/orchestrate/test-bank.md`](../../../eval/orchestrate/test-bank.md) and runs it there with an AI judge. The same questions also exist as ADK test cases in [`eval/orchestrate/tests/`](../../../eval/orchestrate/tests/), with a README. On the Mac, the data API's traces record every tool call the agent makes during the run, and the answers are scored again with the project's own judge. You do not run the evaluation unless a later note asks you to.

## What you do

1. **Finish note 7 first** if you have not: pull, re-register the toolkit, re-add the tools to `gsa-oig-assist-TES` if needed, and re-ask question 5. The evaluation must run against the fixed server. Tell Troy when it is done.
2. **Then hold the agent steady.** Until Troy says the evaluation is finished, do not re-register the toolkit, change the agent's instructions, or add or remove tools. Any change mid-run makes the results mean nothing.
3. **Push your report** with Phases 2 to 4 and the note 7 retest, if it is not pushed yet.

Later notes will cover what remains of the deployment. Wait for them.
