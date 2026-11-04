# Evaluation run: claude-opus-5-5

Data snapshot `d364ff4cb215c6d8`, data as of 2026-11-04. Agent `claude-opus-5-5` at effort `medium`, judge `claude-opus-5-5`. Run 2026-11-04.

| Measure | Result | Scored by |
|---|---|---|
| Questions passing every check | 15 of 23 | Both |
| Exact facts present | 15 of 15 | Code |
| Agrees with the gold reference | 23 of 23 | Judge |
| List precision, mean | 0.67 | Code |
| List recall, exact lists | 1.00 | Code |
| Tool selection | 19 of 19 | Code |
| Caveats and behaviors | 13 of 13 | Judge |
| Citation integrity: every cited report and link exists | 16 of 23 | Code |
| Citation present where required | 7 of 7 | Code |
| Data date stated where required | 5 of 5 | Code |

Questions by category: behavior 5, exact 13, list 2, search 2, workflow 1. Estimated cost at list prices: agent $2.64, judge $0.24.

## By question

| Question | Pass | Facts | Judge | Tools | Citations valid | Seconds | Tool calls |
|---|---|---|---|---|---|---|---|
| count-open-total | yes | yes | yes | yes | yes | 8.8 | 1 |
| count-hfi-2026 | NO | yes | yes | yes | NO | 10.5 | 2 |
| count-peak-year | NO | yes | yes | yes | NO | 9.6 | 2 |
| count-two-states | yes | yes | yes | yes | yes | 16.4 | 5 |
| trend-suicide | yes | yes | yes | yes | yes | 24.0 | 5 |
| closure-vba-median | NO | yes | yes | yes | NO | 12.0 | 2 |
| closure-vha-rate | NO | yes | yes | yes | NO | 10.8 | 2 |
| aging-oit | NO | yes | yes | yes | NO | 15.1 | 3 |
| list-top-offices | NO | yes | yes | yes | NO | 10.3 | 2 |
| facility-el-paso-counts | yes | yes | yes | yes | yes | 18.0 | 2 |
| facility-el-paso-oldest | yes | yes | yes | yes | yes | 10.8 | 2 |
| facility-el-paso-next | yes | yes | yes | yes | yes | 10.9 | 2 |
| list-durham-inspections | NO | - | yes | yes | yes | 19.2 | 2 |
| report-el-paso-2026 | yes | yes | yes | yes | yes | 10.0 | 2 |
| cluster-top-hfi | yes | yes | yes | yes | yes | 17.0 | 3 |
| search-plain-language | yes | - | yes | yes | yes | 21.4 | 2 |
| search-peer-actions | yes | - | yes | yes | yes | 13.6 | 2 |
| brief-el-paso | yes | yes | yes | yes | yes | 36.8 | 4 |
| behave-ambiguous-facility | yes | - | yes | yes | yes | 10.4 | 2 |
| behave-unanswerable | yes | - | yes | - | yes | 19.3 | 3 |
| behave-on-time-rate | NO | - | yes | - | NO | 13.2 | 2 |
| behave-no-rating | yes | - | yes | - | yes | 7.1 | 0 |
| behave-no-prediction | yes | - | yes | - | yes | 23.4 | 2 |

## Tool latency through the server

| Tool | Calls | Median ms | Slowest ms |
|---|---|---|---|
| vaoig_analyze_recommendations | 16 | 268 | 505 |
| vaoig_find_systemic_clusters | 1 | 230 | 230 |
| vaoig_get_dataset_status | 22 | 1242 | 1678 |
| vaoig_get_facility_profile | 7 | 480 | 665 |
| vaoig_get_inspection_brief | 2 | 1932 | 1939 |
| vaoig_get_report | 3 | 409 | 450 |
| vaoig_search_findings | 3 | 382 | 529 |

## What failed

- **count-hfi-2026**: unknown citations: ['https://vaoig.gov/recommendations-all']
- **count-peak-year**: unknown citations: ['https://vaoig.gov/recommendations-all']
- **closure-vba-median**: unknown citations: ['https://vaoig.gov/recommendations-all']
- **closure-vha-rate**: unknown citations: ['https://vaoig.gov/recommendations-all']
- **aging-oit**: unknown citations: ['https://vaoig.gov/recommendations-all']
- **list-top-offices**: unknown citations: ['https://vaoig.gov/recommendations-all']
- **list-durham-inspections**: list: extra ['11-00035-191', '11-00374-239', '11-01416-212', '11-01416-56', '14-03298-20', '21-02458-94'], missed []
- **behave-on-time-rate**: unknown citations: ['https://vaoig.gov/recommendations-all']
