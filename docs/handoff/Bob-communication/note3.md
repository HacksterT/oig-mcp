# Note 3: Phases 0 and 1 accepted, and what to know for Phase 2

Phases 0 and 1 are accepted. Phase 1 also confirmed C2 and the VM's side of C3: the VM reaches the data API through Cloudflare with no proxy.

## Answers to your questions

1. **Push access (A1):** settled. Troy gave you a token that can push `ibm/` branches. Never push to `main`.
2. **Traces on Code Engine:** none on IBM for now. Do not set `MCP_TRACE_DIR`. Every tool call reaches the data API on Troy's Mac with the client and tool name, and the API's traces there record what was asked. Troy may change this later.

## Corrections

- **Dates.** Your reports say 2026-11-10. Use the VM's real date (`date +%F`). In your next commit, rename both reports with `git mv` and fix the Date lines.
- **`MCP_AUTH_TOKEN`.** Do not generate another one. The one in `.env` was generated on this VM on 2026-11-16 and is already new to IBM. Use it for the Code Engine secret, for `verify_deployment.py`, and for the Orchestrate connection, so all three match.
- **Keep `.env` until Phase 3 is done.** Phases 2 and 3 both need the token. Delete `.env`, and any secret file you create for `ibmcloud ce secret create`, after the Orchestrate import succeeds.

## Phase 2

Wait for Troy. He will start Phase 2 tomorrow with his IBM account details. Then follow the handoff's Phase 2, with initials `TES` in every name, and stop after `verify_deployment.py` against the Code Engine URL with the report.
