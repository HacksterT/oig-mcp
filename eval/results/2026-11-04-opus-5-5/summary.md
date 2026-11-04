# Evaluation run: claude-opus-5-5

Data snapshot `d364ff4cb215c6d8`, data as of 2026-11-04. Agent `claude-opus-5-5` at effort `medium`, judge `claude-opus-5-5`. Run 2026-11-04.

| Measure | Result | Scored by |
|---|---|---|
| Questions passing every check | 22 of 23 | Both |
| Exact facts present | 15 of 15 | Code |
| Agrees with the gold reference | 23 of 23 | Judge |
| List precision, mean | 0.71 | Code |
| List recall, exact lists | 1.00 | Code |
| Tool selection | 19 of 19 | Code |
| Caveats and behaviors | 13 of 13 | Judge |
| Citation integrity: every cited report and link exists | 23 of 23 | Code |
| Citation present where required | 7 of 7 | Code |
| Data date stated where required | 5 of 5 | Code |

Questions by category: behavior 5, exact 13, list 2, search 2, workflow 1. Estimated cost at list prices: agent $2.53, judge $0.24.

## By question

| Question | Pass | Facts | Judge | Tools | Citations valid | Seconds | Tool calls |
|---|---|---|---|---|---|---|---|
| count-open-total | yes | yes | yes | yes | yes | 9.9 | 1 |
| count-hfi-2026 | yes | yes | yes | yes | yes | 10.1 | 2 |
| count-peak-year | yes | yes | yes | yes | yes | 12.0 | 2 |
| count-two-states | yes | yes | yes | yes | yes | 11.4 | 3 |
| trend-suicide | yes | yes | yes | yes | yes | 24.0 | 4 |
| closure-vba-median | yes | yes | yes | yes | yes | 12.5 | 2 |
| closure-vha-rate | yes | yes | yes | yes | yes | 10.2 | 2 |
| aging-oit | yes | yes | yes | yes | yes | 9.4 | 2 |
| list-top-offices | yes | yes | yes | yes | yes | 11.0 | 2 |
| facility-el-paso-counts | yes | yes | yes | yes | yes | 15.3 | 2 |
| facility-el-paso-oldest | yes | yes | yes | yes | yes | 11.6 | 2 |
| facility-el-paso-next | yes | yes | yes | yes | yes | 11.8 | 2 |
| list-durham-inspections | NO | - | yes | yes | yes | 14.8 | 2 |
| report-el-paso-2026 | yes | yes | yes | yes | yes | 9.1 | 2 |
| cluster-top-hfi | yes | yes | yes | yes | yes | 19.1 | 4 |
| search-plain-language | yes | - | yes | yes | yes | 24.3 | 4 |
| search-peer-actions | yes | - | yes | yes | yes | 13.6 | 2 |
| brief-el-paso | yes | yes | yes | yes | yes | 36.7 | 3 |
| behave-ambiguous-facility | yes | - | yes | yes | yes | 9.1 | 2 |
| behave-unanswerable | yes | - | yes | - | yes | 14.5 | 3 |
| behave-on-time-rate | yes | - | yes | - | yes | 12.4 | 2 |
| behave-no-rating | yes | - | yes | - | yes | 8.7 | 0 |
| behave-no-prediction | yes | - | yes | - | yes | 21.3 | 2 |

## Tool latency through the server

| Tool | Calls | Median ms | Slowest ms |
|---|---|---|---|
| vaoig_analyze_recommendations | 13 | 221 | 307 |
| vaoig_find_systemic_clusters | 3 | 269 | 270 |
| vaoig_get_dataset_status | 22 | 1166 | 1642 |
| vaoig_get_facility_profile | 6 | 452 | 515 |
| vaoig_get_inspection_brief | 3 | 1867 | 1926 |
| vaoig_get_report | 2 | 412 | 434 |
| vaoig_search_findings | 3 | 357 | 425 |

## What failed

- **list-durham-inspections**: list: extra ['11-00374-239', '11-01416-212', '11-01416-56', '14-03298-20', '21-02458-94'], missed []
