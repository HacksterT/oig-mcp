# Note 13: diagnosing the tool timeouts

Troy says you are seeing tool timeouts. Claude checked the data API's records for your runs: every request your agent's tools made since 23:40 UTC returned successfully, the slowest in about 1.5 seconds, and the server starts in about half a second on the Mac. So the timeouts are happening inside Orchestrate, before or around the tool call, and their exact messages are needed to tell whose limit is being hit.

One real error did reach your run, and it is not a timeout: at 00:06:05 UTC the data API returned a 500 for a count with only the `has_response` or `domain` filter. That is a backend bug, now filed for the data service. Report it as an error on that test; do not work around it.

## What to capture

Finish the current run as it is; do not rerun or change anything because of this. Then add a section to your note 12 report, "Timeouts", with one row per timeout, from the ADK's results (`*.messages.analyze.json`) and its console output:

| Field | What to record |
|---|---|
| Run and test | For example `run-2`, `16-cluster-top-hfi` |
| UTC time | As exact as the output allows |
| Tool | The tool the agent was calling, if any |
| Arguments | The arguments of that call, as recorded |
| Message | The exact error text, copied, including any limit in seconds it states |
| Source | Whether the message comes from Orchestrate's tool runtime, the ADK, or the simulated user, as far as the text shows |

Also record, once: any timeout setting you can find for local toolkits or for `orchestrate evaluations evaluate` (`orchestrate evaluations evaluate --help`, and the ADK's documentation for local MCP toolkits), without changing it.

Claude matches each row to the data API's records by time. If no request reached the data API at that moment, the limit is Orchestrate's start-up or call limit; if a request did, the timing shows how long it took.
