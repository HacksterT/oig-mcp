# Note 9: fetch the test case upload template

Troy is building the evaluation test bank one test at a time in the UI. Orchestrate's API can upload test cases in bulk, but IBM does not publish the file format. Two endpoints matter:

- `GET /v1/orchestrate/agent/test_case/templates`: a CSV template for test cases
- `POST /v1/orchestrate/agent/{agent_id}/test_case`: upload a test case file (multipart, field `file`)

Both take an IAM bearer token. Do not upload anything yet. Fetch the template and the agent's ID, push the template, and stop.

## Steps

From the `oig-mcp` folder. Nothing here prints a secret; do not echo the token or keys.

```bash
git pull --no-rebase origin main
set -a; . ./.env; set +a
TOKEN="$(printf %s "$IBM_API_KEY" | curl -s -X POST https://iam.cloud.ibm.com/identity/token \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode 'grant_type=urn:ibm:params:oauth:grant-type:apikey' \
  --data-urlencode 'apikey@-' | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')"
curl -s -o docs/handoff/Bob-communication/test-case-template.csv -w '%{http_code}\n' \
  -H "Authorization: Bearer $TOKEN" "${IBM_URL%/}/v1/orchestrate/agent/test_case/templates"
orchestrate agents list --verbose
```

1. The `curl` prints an HTTP status. If it is not 200, report the status and the first line of the saved file, then stop.
2. Open `test-case-template.csv` and confirm it holds only column names and sample rows, with no token, key, email, or instance ID. If it holds anything private, do not commit it; describe its columns in your reply instead.
3. From `orchestrate agents list --verbose`, find `gsa-oig-assist-TES` and note its ID. Do not commit the ID; tell Troy it was found.
4. Commit and push the template to `ibm/deploy`: `git add docs/handoff/Bob-communication/test-case-template.csv && git commit -m "Add the Orchestrate test case template" && git push origin ibm/deploy`.
5. Tell Troy it is pushed. Claude will generate the 24 test cases in that format and send the upload steps in the next note.

If the template endpoint fails, a second route: Troy opens **Modify JSON** on a saved test (Q01), copies the JSON into `docs/handoff/Bob-communication/q01-test.json` on this VM, and you check it for private values the same way, then push it.
