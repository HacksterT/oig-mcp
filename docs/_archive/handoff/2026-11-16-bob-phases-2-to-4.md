# F05 Phases 2–4: Deploy to watsonx Orchestrate and end-to-end test

**Author:** Bob
**Date:** 2026-11-16
**Assignment or phase:** F05 Phases 2–4: local MCP toolkit, Orchestrate registration, agent, end-to-end
**Branch:** `ibm/deploy`

## Summary

The oig-mcp server was registered in watsonx Orchestrate as a local (stdio) MCP toolkit, skipping Code Engine entirely. A test agent answered five of the six Phase 4 questions correctly; question 5 ("New York VA") exposed a model tool-use issue where the agent searched with too specific a name and got no match instead of a list of facilities. The data API, all seven tools, and the server's behavior are correct.

## What was done

1. Reviewed `https://github.com/GSA-TTS/mcp-hackathon-template/tree/main/deploy/ibm` and identified three deployment paths. Chose `local-mcp-toolkit` (stdio) because the IBM Cloud account (the Orchestrate tenant) had no resource group or Container Registry namespace provisioned, and the hackathon helper script API returned no record for any identifier tried. Troy confirmed stdio was acceptable.
2. Created a first draft of `deploy/ibm/local-mcp-toolkit/` files; committed and ran the register script. The toolkit imported successfully but all tool calls returned "data API could not be reached."
3. Diagnosed: the first toolkit used a bearer connection, which does nothing over stdio. The server had no data API credentials and fell back to its default (unreachable) address.
4. Per note6 from Troy's local agent: removed notes 4 and 5 (contained private details not suitable for a public repo), removed the first toolkit draft, and pulled the fixed kit from `main`.
5. Ran the fixed `register-toolkit.sh`: created key_value connection `oig_mcp_data_TES` with the four data API values; re-imported `oig_mcp_TES` with the connection attached; removed the unused bearer connection `oig_mcp_auth_TES`.
6. In the Orchestrate UI: opened agent `gsa-oig-assist-TES`, re-added all 7 tools from `oig_mcp_TES`.
7. Asked the six Phase 4 questions in order and recorded answers.

## Resources created or changed

| Kind | Name | URL or location |
|---|---|---|
| Orchestrate toolkit | `oig_mcp_TES` | Orchestrate instance (ca-tor), 7 tools, local stdio |
| Orchestrate connection | `oig_mcp_data_TES` | key_value, draft and live, 4 data API credentials |
| Orchestrate agent | `gsa-oig-assist-TES` | Global workspace, 7 tools, no project-specific instructions |
| Files added | `deploy/ibm/local-mcp-toolkit/` | `server.py`, `toolkit.yaml`, `register-toolkit.sh`, `README.md` |

## Checks

| Check | Result | Notes |
|---|---|---|
| Toolkit imports with 7 tools | Pass | `orchestrate toolkits list` confirms `oig_mcp_TES` with 7 tools and App ID `oig_mcp_data_TES` |
| Q1: OIG dataset status | Pass | 4,415 reports, 15,649 recommendations, data as of 2026-11-04; 19-row open-count discrepancy noted correctly |
| Q2: HFI recommendations in 2026 | Pass | 148 total, 80 open — matches expected values exactly |
| Q3: Medication cart findings with links | Pass | 8 reports cited with report numbers and vaoig.gov links; data date stated |
| Q4: El Paso inspection brief | Pass | Used `vaoig_get_inspection_brief`; labeled next window as estimate (2028-01-16 ± a few months); did not predict findings; cited 4 open recommendations and 5 peer clusters |
| Q5: New York VA findings | Partial | See findings below |
| Q6: Percentage of missed target dates | Pass | Correctly refused to give a percentage and explained the data cannot establish it |

## Phase 4 question answers (full)

### Q1 — What is the status of the OIG dataset?

> The OIG dataset is currently as of 2026-11-04. Total Recommendations: 15,649 (567 open, 14,925 closed-implemented, 157 closed-not-implemented). Total Reports: 4,415 (2,229 with recommendations). Facilities covered: 159. Inspections: 1,232. PDF Documents: 2,214 (~89,188 pages). Clusters: 283. Facility Responses: 11,264. Notes: OIG's public dashboard lists 586 open recommendations vs. this dataset's 567; the 19-row discrepancy comes from blank rows on the OIG site and is within tolerance.

### Q2 — HFI recommendations published in 2026, total and open

> Total recommendations: 148. Open: 80. Closed-implemented: 68. Closed-not-implemented: 0. Filtered to report type `healthcare-facility-inspection`, published 2026-01-01 to 2026-12-31.

### Q3 — Has OIG cited unlocked medication carts?

> Yes. Eight reports cited, including: 13-03653-91 (Atlanta VAMC), 15-00606-495 (Battle Creek VAMC), 13-00279-156 (VA Palo Alto), 14-00689-142 (Orlando VAMC), 16-00106-211 (Charlie Norwood VAMC), 15-00071-158 (West Palm Beach VAMC), 20-03593-140 (Louis A. Johnson VAMC, Clarksburg WV), 12-03075-52 (Miami VA). All with vaoig.gov links. Data as of 2026-11-04.

### Q4 — Prepare VA El Paso for next OIG inspection

> Used `vaoig_get_inspection_brief`. Most recent HFI: report 25-00193-155, published 2026-07-16. Estimated next window: 2028-01-16 ± a few months (labeled as estimate). 4 open recommendations: clean/safe environment (EOC), timely TES secondary screenings, video surveillance for data center, water-detection sensors in data center. Top peer clusters: test-result communication workflows (clusters 260, 261), clean environment/infection control (262), leadership stability (263, 264). Included pre-inspection checklist, action items, and resource links.

### Q5 — What has OIG found at the New York VA?

> "The OIG's public search tool did not return any specific findings for facilities in New York when filtering by state=NY. This means that, within the current OIG dataset (as of 2026-11-04), there are no reported findings that can be directly retrieved for 'the New York VA.'"

### Q6 — What percentage of VHA recommendations missed their target completion dates?

> "I'm sorry, but the dataset does not include the information needed to determine whether a recommendation met its target completion date. Consequently, I can't calculate the percentage of VHA recommendations that missed their target dates."

## Findings and recommendations

**Q5 is a tool-use failure, not a server failure.** The server's `vaoig_get_facility_profile` tool correctly returns 9 New York facilities when called with the string `"New York"` (verified from the VM). The agent called the tool with `"New York VA"` (exact match, no results) instead of `"New York"` (partial match, 9 results). The tool's multi-match response — listing all matching facilities and asking the user to specify — was never reached. This is assumption D10 from the handoff: Orchestrate's model may not make optimal tool calls.

**The server's behavior is correct.** Questions 1–4 and 6 all passed with the right data, correct caveats, citations, and refusals. The tool descriptions were sufficient for the model on 5 of 6 questions.

**Code Engine path remains blocked.** The IBM Cloud account had no resource group and the helper script API returned no record. Troy confirmed the stdio path was acceptable for this deployment.

**No secrets were committed.** Notes 4 and 5 were removed per note6 before this report was written.

**Bearer connection vs. key_value:** Over stdio, a bearer connection does nothing — credentials must be key_value so Orchestrate passes them as environment variables. This was the root cause of the first failed deployment and is now documented here for future reference.

## Questions for Troy

1. Question 5: The agent called the tool with too specific a name ("New York VA") and got no match. Should the tool description be updated to encourage partial-name searches, or is this acceptable behavior to note and leave as-is?
2. Should the full evaluation (`eval/phoenix/run_experiment.py`) be run now? It needs an Anthropic key and a URL — for stdio there is no URL, so it may need to run against the local server instead.

## Proposed next step

If Troy is satisfied with the Phase 4 results, the deployment is complete. Optional follow-on:
- Run the full 24-question evaluation locally against the server to get a score comparable to the Mac results (23/24).
- Update the tool description for `vaoig_get_facility_profile` to hint that partial names work better, if Troy agrees.

## Troy's response

(Troy fills this in.)
