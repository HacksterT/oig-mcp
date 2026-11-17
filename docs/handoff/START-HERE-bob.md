# Start here, Bob

oig-mcp, an MCP server over public VA Office of Inspector General data, runs in watsonx Orchestrate as a local (stdio) toolkit, registered from this VM with [`deploy/ibm/local-mcp-toolkit/register-toolkit.sh`](../../deploy/ibm/local-mcp-toolkit/README.md). Orchestrate runs the server itself and passes it the data API's settings from a key_value connection. IBM Code Engine was planned and not used: the account had no resource group, registry namespace, or Code Engine project. Your reports on that work are in this folder: Phase 0, Phase 1, and Phases 2 to 4, dated 2026-11-16.

Repository: https://github.com/HacksterT/oig-mcp (branch `main`, public).

## How work reaches you now

Troy leaves numbered notes in [`Bob-communication/`](Bob-communication/). When he says "read note N", run `git pull --no-rebase origin main`, then read and follow it. A newer note wins over anything older. Notes already carried out are in [`docs/_archive/Bob-notes/`](../_archive/Bob-notes/).

Background and the rules for working here are in [`../project-overview.md`](../project-overview.md). Where your own skills differ from it on something specific to this project, it wins. The original Code Engine plan, [`2026-11-04-troy-bob-deployment-handoff.md`](../_archive/handoff/2026-11-04-troy-bob-deployment-handoff.md), is kept as a record and no longer describes the deployment.

## Standing rules

- Work on `ibm/deploy`. Never push to `main`, and never force-push.
- Changes to repository files go onto `main` from Troy's Mac. Report the problem with the exact error and your proposed fix, and stop. Your own reports are the exception.
- Use the initials `TES` in every IBM resource name.
- Never put a secret, token, account or instance or agent ID, or email address in a commit, a log, or a report. Confirm you received a secret without repeating its value.
- If something fails, send Troy the exact error and stop. Do not weaken authentication, add a proxy, or change the transport to get past it. Ask before creating anything paid.
- Write reports with [`TEMPLATE.md`](TEMPLATE.md), named `YYYY-MM-DD-bob-<topic>.md`, unless a note gives another name.
