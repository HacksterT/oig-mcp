# Evaluation run: claude-sonnet-5-5

Data snapshot `d364ff4cb215c6d8`, data as of 2026-11-04. Agent `claude-sonnet-5-5` at effort `medium`, judge `claude-opus-5-5`. Run 2026-11-04.

| Measure | Result | Scored by |
|---|---|---|
| Questions passing every check | 22 of 23 | Both |
| Exact facts present | 15 of 15 | Code |
| Agrees with the gold reference | 23 of 23 | Judge |
| List precision, mean | 0.65 | Code |
| List recall, exact lists | 1.00 | Code |
| Tool selection | 19 of 19 | Code |
| Caveats and behaviors | 13 of 13 | Judge |
| Citation integrity: every cited report and link exists | 22 of 23 | Code |
| Citation present where required | 7 of 7 | Code |
| Data date stated where required | 5 of 5 | Code |

Questions by category: behavior 5, exact 13, list 2, search 2, workflow 1. Estimated cost at list prices: agent $1.15, judge $0.23.

## By question

| Question | Pass | Facts | Judge | Tools | Citations valid | Seconds | Tool calls |
|---|---|---|---|---|---|---|---|
| count-open-total | yes | yes | yes | yes | yes | 4.2 | 1 |
| count-hfi-2026 | yes | yes | yes | yes | yes | 5.8 | 2 |
| count-peak-year | yes | yes | yes | yes | yes | 5.3 | 2 |
| count-two-states | yes | yes | yes | yes | yes | 5.5 | 3 |
| trend-suicide | yes | yes | yes | yes | yes | 9.7 | 2 |
| closure-vba-median | yes | yes | yes | yes | yes | 6.6 | 2 |
| closure-vha-rate | yes | yes | yes | yes | yes | 5.3 | 2 |
| aging-oit | yes | yes | yes | yes | yes | 5.8 | 2 |
| list-top-offices | yes | yes | yes | yes | yes | 4.9 | 2 |
| facility-el-paso-counts | yes | yes | yes | yes | yes | 8.4 | 2 |
| facility-el-paso-oldest | yes | yes | yes | yes | yes | 6.7 | 2 |
| facility-el-paso-next | yes | yes | yes | yes | yes | 4.7 | 1 |
| list-durham-inspections | NO | - | yes | yes | NO | 6.5 | 2 |
| report-el-paso-2026 | yes | yes | yes | yes | yes | 3.9 | 1 |
| cluster-top-hfi | yes | yes | yes | yes | yes | 11.1 | 3 |
| search-plain-language | yes | - | yes | yes | yes | 12.1 | 2 |
| search-peer-actions | yes | - | yes | yes | yes | 7.4 | 2 |
| brief-el-paso | yes | yes | yes | yes | yes | 16.9 | 2 |
| behave-ambiguous-facility | yes | - | yes | yes | yes | 17.2 | 3 |
| behave-unanswerable | yes | - | yes | - | yes | 6.0 | 2 |
| behave-on-time-rate | yes | - | yes | - | yes | 7.3 | 2 |
| behave-no-rating | yes | - | yes | - | yes | 5.8 | 0 |
| behave-no-prediction | yes | - | yes | - | yes | 10.8 | 2 |

## Tool latency through the server

| Tool | Calls | Median ms | Slowest ms |
|---|---|---|---|
| vaoig_analyze_recommendations | 10 | 242 | 428 |
| vaoig_find_systemic_clusters | 1 | 262 | 262 |
| vaoig_get_dataset_status | 20 | 1150 | 1410 |
| vaoig_get_facility_profile | 7 | 507 | 528 |
| vaoig_get_inspection_brief | 2 | 1528 | 1606 |
| vaoig_get_report | 1 | 455 | 455 |
| vaoig_search_findings | 3 | 363 | 456 |

## What failed

- **list-durham-inspections**: list: extra ['11-00374-239', '11-01416-212', '11-01416-56', '14-03298-20', '21-02458-94'], missed []; unknown citations: ['https://vaoig.gov/reports/<report-type']
