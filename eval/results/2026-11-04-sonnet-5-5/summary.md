# Evaluation run: claude-sonnet-5-5

Data snapshot `2bb10bd321e08dfc`, data as of 2026-11-04. Agent `claude-sonnet-5-5` at effort `medium`, judge `claude-opus-5-5`. Run 2026-11-04.

| Measure | Result | Scored by |
|---|---|---|
| Questions passing every check | 23 of 24 | Both |
| Exact facts present | 16 of 16 | Code |
| Agrees with the gold reference | 23 of 24 | Judge |
| List precision, mean | 0.77 | Code |
| List recall, exact lists | 1.00 | Code |
| Tool selection | 20 of 20 | Code |
| Caveats and behaviors | 14 of 14 | Judge |
| Citation integrity: every cited report and link exists | 24 of 24 | Code |
| Citation present where required | 7 of 8 | Code |
| Data date stated where required | 5 of 5 | Code |

Questions by category: behavior 5, exact 14, list 2, search 2, workflow 1. Estimated cost at list prices: agent $1.08, judge $0.23.

## By question

| Question | Pass | Facts | Judge | Tools | Citations valid | Seconds | Tool calls |
|---|---|---|---|---|---|---|---|
| count-open-total | yes | yes | yes | yes | yes | 5.7 | 1 |
| count-hfi-2026 | yes | yes | yes | yes | yes | 7.4 | 2 |
| count-peak-year | yes | yes | yes | yes | yes | 7.0 | 2 |
| count-two-states | yes | yes | yes | yes | yes | 8.1 | 3 |
| trend-suicide | yes | yes | yes | yes | yes | 10.3 | 3 |
| closure-vba-median | yes | yes | yes | yes | yes | 6.7 | 2 |
| closure-vha-rate | yes | yes | yes | yes | yes | 6.8 | 2 |
| aging-oit | yes | yes | yes | yes | yes | 6.2 | 2 |
| list-top-offices | yes | yes | yes | yes | yes | 6.2 | 2 |
| facility-el-paso-counts | yes | yes | yes | yes | yes | 10.1 | 2 |
| facility-el-paso-oldest | yes | yes | yes | yes | yes | 7.8 | 2 |
| facility-el-paso-next | yes | yes | yes | yes | yes | 6.5 | 1 |
| facility-clean-inspection | yes | yes | yes | yes | yes | 6.5 | 2 |
| list-durham-inspections | NO | - | NO | yes | yes | 8.8 | 2 |
| report-el-paso-2026 | yes | yes | yes | yes | yes | 4.6 | 1 |
| cluster-top-hfi | yes | yes | yes | yes | yes | 11.8 | 3 |
| search-plain-language | yes | - | yes | yes | yes | 15.8 | 2 |
| search-peer-actions | yes | - | yes | yes | yes | 8.1 | 2 |
| brief-el-paso | yes | yes | yes | yes | yes | 18.5 | 2 |
| behave-ambiguous-facility | yes | - | yes | yes | yes | 12.7 | 3 |
| behave-unanswerable | yes | - | yes | - | yes | 8.2 | 2 |
| behave-on-time-rate | yes | - | yes | - | yes | 6.4 | 1 |
| behave-no-rating | yes | - | yes | - | yes | 4.5 | 0 |
| behave-no-prediction | yes | - | yes | - | yes | 13.4 | 2 |

## Tool latency through the server

| Tool | Calls | Median ms | Slowest ms |
|---|---|---|---|
| vaoig_analyze_recommendations | 11 | 334 | 1412 |
| vaoig_find_systemic_clusters | 1 | 230 | 230 |
| vaoig_get_dataset_status | 19 | 2544 | 3852 |
| vaoig_get_facility_profile | 7 | 560 | 1966 |
| vaoig_get_inspection_brief | 4 | 2294 | 3452 |
| vaoig_get_report | 1 | 826 | 826 |
| vaoig_search_findings | 3 | 838 | 1694 |

## What failed

- **list-durham-inspections**: list: extra ['11-00374-239', '11-01416-212', '11-01416-56', '14-03298-20', '21-02458-94'], missed []; judge: The answer lists exactly the eight gold report numbers, but it also states there are 9 such reports, which contradicts both the gold and its own list of 8.; no report number and link together
