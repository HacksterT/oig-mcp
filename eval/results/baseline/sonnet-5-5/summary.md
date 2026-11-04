# Evaluation run: claude-sonnet-5-5

Data snapshot `d364ff4cb215c6d8`, data as of 2026-11-04. Agent `claude-sonnet-5-5` at effort `medium`, judge `claude-opus-5-5`. Run 2026-11-04.

| Measure | Result | Scored by |
|---|---|---|
| Questions passing every check | 17 of 23 | Both |
| Exact facts present | 14 of 15 | Code |
| Agrees with the gold reference | 22 of 23 | Judge |
| List precision, mean | 0.72 | Code |
| List recall, exact lists | 1.00 | Code |
| Tool selection | 19 of 19 | Code |
| Caveats and behaviors | 12 of 13 | Judge |
| Citation integrity: every cited report and link exists | 18 of 23 | Code |
| Citation present where required | 7 of 7 | Code |
| Data date stated where required | 5 of 5 | Code |

Questions by category: behavior 5, exact 13, list 2, search 2, workflow 1. Estimated cost at list prices: agent $1.19, judge $0.24.

## By question

| Question | Pass | Facts | Judge | Tools | Citations valid | Seconds | Tool calls |
|---|---|---|---|---|---|---|---|
| count-open-total | yes | yes | yes | yes | yes | 6.8 | 2 |
| count-hfi-2026 | NO | yes | yes | yes | NO | 5.7 | 2 |
| count-peak-year | NO | yes | yes | yes | NO | 5.4 | 2 |
| count-two-states | yes | yes | yes | yes | yes | 4.8 | 3 |
| trend-suicide | yes | yes | yes | yes | yes | 9.0 | 2 |
| closure-vba-median | NO | yes | yes | yes | NO | 6.5 | 2 |
| closure-vha-rate | yes | yes | yes | yes | yes | 4.6 | 2 |
| aging-oit | yes | yes | yes | yes | yes | 5.1 | 2 |
| list-top-offices | yes | yes | yes | yes | yes | 6.1 | 2 |
| facility-el-paso-counts | yes | yes | yes | yes | yes | 8.3 | 2 |
| facility-el-paso-oldest | yes | yes | yes | yes | yes | 5.3 | 2 |
| facility-el-paso-next | yes | yes | yes | yes | yes | 5.4 | 2 |
| list-durham-inspections | NO | - | NO | yes | NO | 6.4 | 1 |
| report-el-paso-2026 | yes | yes | yes | yes | yes | 4.1 | 1 |
| cluster-top-hfi | NO | NO | yes | yes | yes | 13.3 | 5 |
| search-plain-language | yes | - | yes | yes | yes | 12.5 | 2 |
| search-peer-actions | yes | - | yes | yes | yes | 6.8 | 2 |
| brief-el-paso | yes | yes | yes | yes | yes | 17.0 | 2 |
| behave-ambiguous-facility | yes | - | yes | yes | yes | 16.2 | 3 |
| behave-unanswerable | yes | - | yes | - | yes | 7.0 | 2 |
| behave-on-time-rate | NO | - | yes | - | NO | 7.5 | 2 |
| behave-no-rating | yes | - | yes | - | yes | 4.1 | 0 |
| behave-no-prediction | yes | - | yes | - | yes | 11.5 | 2 |

## Tool latency through the server

| Tool | Calls | Median ms | Slowest ms |
|---|---|---|---|
| vaoig_analyze_recommendations | 10 | 216 | 277 |
| vaoig_find_systemic_clusters | 3 | 209 | 258 |
| vaoig_get_dataset_status | 21 | 1074 | 1274 |
| vaoig_get_facility_profile | 6 | 412 | 453 |
| vaoig_get_inspection_brief | 3 | 1410 | 1419 |
| vaoig_get_report | 1 | 313 | 313 |
| vaoig_search_findings | 3 | 361 | 470 |

## What failed

- **count-hfi-2026**: unknown citations: ['https://vaoig.gov/recommendations-all']
- **count-peak-year**: unknown citations: ['https://vaoig.gov/recommendations-all']
- **closure-vba-median**: unknown citations: ['https://vaoig.gov/recommendations-all']
- **list-durham-inspections**: list: extra ['11-00035-191', '11-00374-239', '11-01416-212', '11-01416-56', '14-03298-20', '21-02458-94'], missed []; judge: The answer includes all seven gold report numbers but presents a materially larger list of 14 reports as Durham inspections, including 11-00035-191 grouped with the gold program inspections without any caveat, so its exhaustive list does not match the gold set.; unknown citations: ['https://vaoig.gov/reports/<report-type']
- **cluster-top-hfi**: missing fact: El Paso membership
- **behave-on-time-rate**: caveat: Although it explains that the data cannot establish missed deadlines, it still computes and presents 'about 86%' as the share closed after or open past target 'if you ignored the caveats', which effectively supplies a quotable miss-rate percentage.; unknown citations: ['https://vaoig.gov/recommendations-all']
