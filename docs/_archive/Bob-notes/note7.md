# Note 7: re-register for the question 5 fix

Question 5 failed for three reasons, now fixed on `main`:

1. The agent searched instead of opening the facility. The tool descriptions now say that "what has OIG found at <a place>" goes to `vaoig_get_facility_profile`.
2. The facility lookup matched only exact text, and no facility is named "New York VA". It now retries without words such as "VA", "VAMC", "medical center", and "hospital", so "New York VA" returns the ten New York facilities and asks which one is meant.
3. The state filter expected "New York" and silently matched nothing for "NY". It now accepts postal codes.

Tested on the Mac over stdio against the live data API.

## Steps

1. `git pull --no-rebase origin main`
2. `bash deploy/ibm/local-mcp-toolkit/register-toolkit.sh`
3. In the Orchestrate UI, re-add the `oig_mcp_TES` tools to agent `gsa-oig-assist-TES` if they dropped off.
4. Ask question 5 again, "What has OIG found at the New York VA?", then question 6 if you have not yet. Add both full answers to your report under a "After the note 7 fix" heading, keeping the first answer to question 5 as it was.
5. Push the report to `ibm/deploy` and tell Troy.
