# Note 12: test uploading one test case to the Orchestrate UI

`eval/orchestrate/ui-tests/` now holds all 24 questions in the UI's JSON format, modeled on your `q01-test.json` export: same fields at every level, the response summary switched on, each question's critical argument, and keywords. Troy wants them in the UI's test list so he can run evaluations there with his LLM-as-a-Judge metrics.

Test the upload with **one** file, Q15, and stop.

```bash
git pull --no-rebase origin main
set -a; . ./.env; set +a
TOKEN="$(printf %s "$IBM_API_KEY" | curl -s -X POST https://iam.cloud.ibm.com/identity/token \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode 'grant_type=urn:ibm:params:oauth:grant-type:apikey' \
  --data-urlencode 'apikey@-' | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')"
AGENT_ID="<the gsa-oig-assist-TES ID you found for note 9>"
curl -s -w '\nHTTP %{http_code}\n' -H "Authorization: Bearer $TOKEN" \
  -F "file=@eval/orchestrate/ui-tests/Q15-report-el-paso-2026.json;type=application/json" \
  "${IBM_URL%/}/v1/orchestrate/agent/$AGENT_ID/test_case"
```

1. **HTTP 200:** the response lists `test_case_ids` and `total_test_cases`. Ask Troy to open the agent's Evaluate tab and confirm the Q15 test appears with its response summary, the `report_number` match set to strict, and the switch on. Report back and stop. Troy decides whether to upload the rest.
2. **HTTP 422 or another error:** report the status and the response body (it describes what the API expected; check it holds nothing private first). Then try the same file wrapped as a list, `[ ... ]`, saved to a temporary file outside the repository, once, and report that result too.
3. Do not upload anything else, and do not commit the agent ID or the token.
