# Bob status — Note 14

| UTC time | Step | Status | Note |
|---|---|---|---|
| 2026-11-17T17:51:41Z | 1 | done | Toolkit oig_mcp_TES re-imported from main (eval-final-1 code). 7 tools registered against oig_mcp_data_TES connection. Troy re-added all 7 tools to gsa-oig-assist-TES. |
| 2026-11-17T17:57:52Z | 2 | done | Step 2 verified: OIT open recommendations = 57. Correct. |
| 2026-11-17T17:57:52Z | 2b | done | NY VA: no form; agent listed multiple NY facilities in text and asked which one. CA VA: no form; agent returned report examples across CA facilities (not a facility list), ending with a suggestion to run vaoig_analyze_recommendations for a complete list. |
| 2026-11-17T19:05:00Z | 4+5 | done | Both runs complete: 30/30 tests each (24 original + 6 adversarial run separately due to ADK parallel-execution token drop, then merged). debug/ removed, instance ID/URL/paths redacted, pushed to ibm/deploy. One tool error logged: trend-suicide run-1 hit "connection refused" on second vaoig_analyze_recommendations call; agent answered correctly from first call. |
| 2026-11-17T19:05:00Z | 6 | skipped | Demo recording not done today — Troy will record before the presentation. |
| 2026-11-17T18:56:40Z | 7 | done | Report written to docs/handoff/2026-11-17-bob-orchestrate-rerun.md and pushed to ibm/deploy. All steps complete. |
