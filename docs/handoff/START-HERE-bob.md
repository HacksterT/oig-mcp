# Start here, Bob

You are deploying oig-mcp, an MCP server over public VA Office of Inspector General data, to IBM Code Engine, and registering it in watsonx Orchestrate. The server is built and tested on Troy's Mac. Nothing has run on IBM yet.

Repository: https://github.com/HacksterT/oig-mcp (branch `main`)

Read these two files before doing anything else, in this order:

1. [`2026-11-04-troy-bob-deployment-handoff.md`](2026-11-04-troy-bob-deployment-handoff.md): your steps, what has been tested, and every assumption about IBM
2. [`../project-overview.md`](../project-overview.md): background and the rules for working here

Where your own skills differ from these documents on something specific to this project, these documents win.

Work through Phases 0 to 4 in the handoff, one at a time. Stop at the end of each phase and write a report using [`TEMPLATE.md`](TEMPLATE.md), including which assumptions held and which were wrong, with exact error text. Work on an `ibm/` branch. Never push to `main`.

Use the initials `TES` in every IBM resource name.

Troy will give you these values directly when you need them: the data API URL, the Cloudflare client ID and secret, his IBM account details, and the Orchestrate URL and key. Generate `MCP_AUTH_TOKEN` yourself, as the handoff describes. Confirm you received a secret without repeating its value, and never put a secret in a commit, a log, or a report.

If the server cannot reach the data API or Orchestrate rejects the connection, stop and send Troy the exact error. Do not weaken authentication, add a proxy, or change the transport to get past it. Ask before creating anything paid that the handoff does not list.

Start now with Phase 0, and tell Troy what you need from him for Phase 1.
