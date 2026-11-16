# Note 6: the local toolkit, fixed, and your branch reset

Troy has chosen the local (stdio) toolkit, so Code Engine is not needed. Thank you for finding that route.

## What was wrong

Not the 307. The server never calls a path with a trailing slash; it calls `meta`, `search`, `facilities`, `reports/<id>`, `clusters/<id>`, and `taxonomy/<facet>`. The real cause: the toolkit had no connection attached, so the server ran inside Orchestrate with no data API address or credentials, fell back to its local default, and answered that the data API was not reachable. Over stdio a bearer connection does nothing. A local toolkit takes a **key_value** connection, and Orchestrate passes each key to the server as an environment variable.

The fixed kit is on `main` in `deploy/ibm/local-mcp-toolkit/`. It was tested on the Mac exactly as Orchestrate runs it: a clean environment built only from the pinned requirements, the server started over stdio with only the four values, and live tool calls.

## Remove notes 4 and 5

Notes 4 and 5 put private details into this public repository: an email address, IBM account and instance IDs, and the data API's address. Remove them from the branch (step 1). Do not refer to those details in any committed file again; write "Troy's account", "the Orchestrate instance", "the data API".

## Steps

1. Remove notes 4 and 5 and your first toolkit draft, then take the fixed kit from `main`. Your `.env` files are untracked and are not touched:
   ```bash
   git rm -r -q deploy/ibm/local-mcp-toolkit docs/handoff/Bob-communication/note4.md docs/handoff/Bob-communication/note5.md
   git commit -m "Remove notes 4 and 5 and the first toolkit draft"
   git pull --no-rebase origin main
   git push origin ibm/deploy
   ls deploy/ibm/local-mcp-toolkit
   ```
   Expect `README.md  register-toolkit.sh  server.py  toolkit.yaml`. If the pull reports a conflict, stop and tell Troy the exact message.
2. Run `bash deploy/ibm/local-mcp-toolkit/register-toolkit.sh`. It reads the four data API values from `.env`, and the Orchestrate URL and key from `IBM_URL` and `IBM_API_KEY` there. If environment activation fails, the Orchestrate key differs from `IBM_API_KEY`: run it again with `WXO_API_KEY` exported. It prints no secret.
3. Remove the unused bearer connection: `orchestrate connections remove -a oig_mcp_auth_TES`.
4. In the Orchestrate UI, open agent `gsa-oig-assist-TES` and re-add the `oig_mcp_TES` tools if the re-import removed them.
5. Phase 4: ask the handoff's six questions in order and record each full answer.
6. Write one report, `docs/handoff/<date>-bob-phases-2-to-4.md`, using `TEMPLATE.md`. Commit and push to `ibm/deploy`, then tell Troy.

If the first question still says the data API cannot be reached, or returns status 401 or 403, put the exact answer in the report and stop.
