# Evaluation run: claude-opus-5-5

Data snapshot `2bb10bd321e08dfc`, data as of 2026-11-04. Agent `claude-opus-5-5` at effort `medium`, judge `claude-opus-5-5`. Run 2026-11-10.

| Measure | Result | Scored by |
|---|---|---|
| Questions passing every check | 23 of 24 | Both |
| Exact facts present | 16 of 16 | Code |
| Agrees with the gold reference | 24 of 24 | Judge |
| List precision, mean | 0.77 | Code |
| List recall, exact lists | 1.00 | Code |
| Tool selection | 20 of 20 | Code |
| Caveats and behaviors | 14 of 14 | Judge |
| Citation integrity: every cited report and link exists | 24 of 24 | Code |
| Citation present where required | 8 of 8 | Code |
| Data date stated where required | 5 of 5 | Code |

Questions by category: behavior 5, exact 14, list 2, search 2, workflow 1. Estimated cost at list prices: agent $2.83, judge $0.25.

## By question

| Question | Pass | Facts | Judge | Tools | Citations valid | Seconds | Tool calls |
|---|---|---|---|---|---|---|---|
| count-open-total | yes | yes | yes | yes | yes | 11.3 | 2 |
| count-hfi-2026 | yes | yes | yes | yes | yes | 11.6 | 3 |
| count-peak-year | yes | yes | yes | yes | yes | 16.6 | 2 |
| count-two-states | yes | yes | yes | yes | yes | 10.1 | 3 |
| trend-suicide | yes | yes | yes | yes | yes | 23.5 | 5 |
| closure-vba-median | yes | yes | yes | yes | yes | 11.8 | 2 |
| closure-vha-rate | yes | yes | yes | yes | yes | 11.0 | 2 |
| aging-oit | yes | yes | yes | yes | yes | 11.6 | 3 |
| list-top-offices | yes | yes | yes | yes | yes | 8.3 | 2 |
| facility-el-paso-counts | yes | yes | yes | yes | yes | 15.4 | 2 |
| facility-el-paso-oldest | yes | yes | yes | yes | yes | 11.4 | 2 |
| facility-el-paso-next | yes | yes | yes | yes | yes | 14.2 | 2 |
| facility-clean-inspection | yes | yes | yes | yes | yes | 26.5 | 2 |
| list-durham-inspections | NO | - | yes | yes | yes | 16.3 | 2 |
| report-el-paso-2026 | yes | yes | yes | yes | yes | 16.8 | 2 |
| cluster-top-hfi | yes | yes | yes | yes | yes | 19.0 | 4 |
| search-plain-language | yes | - | yes | yes | yes | 22.7 | 3 |
| search-peer-actions | yes | - | yes | yes | yes | 12.3 | 2 |
| brief-el-paso | yes | yes | yes | yes | yes | 33.4 | 2 |
| behave-ambiguous-facility | yes | - | yes | yes | yes | 9.2 | 2 |
| behave-unanswerable | yes | - | yes | - | yes | 13.3 | 3 |
| behave-on-time-rate | yes | - | yes | - | yes | 12.9 | 2 |
| behave-no-rating | yes | - | yes | - | yes | 7.7 | 0 |
| behave-no-prediction | yes | - | yes | - | yes | 29.0 | 2 |

## Tool latency through the server

| Tool | Calls | Median ms | Slowest ms |
|---|---|---|---|
| vaoig_analyze_recommendations | 16 | 152 | 232 |
| vaoig_find_systemic_clusters | 3 | 161 | 221 |
| vaoig_get_dataset_status | 23 | 270 | 423 |
| vaoig_get_facility_profile | 8 | 312 | 411 |
| vaoig_get_inspection_brief | 2 | 1983 | 2026 |
| vaoig_get_report | 1 | 179 | 179 |
| vaoig_search_findings | 3 | 332 | 348 |

## What failed

- **list-durham-inspections**: list: extra ['11-00374-239', '11-01416-212', '11-01416-56', '14-03298-20', '21-02458-94'], missed []
