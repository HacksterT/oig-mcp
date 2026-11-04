# MCP Test — Q&A Log, Follow-up Round (qna2.md)

Continuing the OIG-MCP evaluation (VA Office of Inspector General, served over HTTP). Round one (Q1–Q17) is logged in `qna.md`; this file is the follow-up round.

_Tool note: the server was reloaded and is now exposed as `OIG-MCP3`, so tools are prefixed `mcp__OIG_MCP3__` (the handoff's `mcp__OIG_MCP__` prefix is stale). Behavior is otherwise unchanged._

_Format: each question lists the exact MCP tools it used under a `**Tools used:**` line, and carries an OBSERVATIONS section capturing tool quirks and guardrails._

| Q | Tools used |
|---|---|
| Q1 | `vaoig_get_dataset_status` |
| Q2 | `vaoig_analyze_recommendations` (x2) |
| Q3 | `vaoig_analyze_recommendations` (x2: Texas + North Carolina) |
| Q4 | `vaoig_analyze_recommendations` (action_office=VBA, group_by=office) |
| Q5 | `vaoig_analyze_recommendations` (action_office=VHA, group_by=office) |
| Q6 | `vaoig_get_facility_profile` |
| Q7 | `vaoig_get_report` |
| Q8 | `vaoig_find_systemic_clusters` (x2: list HFI + open cluster 260) |
| Q9 | `vaoig_search_findings` |
| Q10 | `vaoig_search_findings` (re-read same result's `corrective_action`) |
| Q11 | `vaoig_get_inspection_brief` |
| Q12 | `vaoig_analyze_recommendations` (keywords="suicide", group_by=year) |
| Q13 | `vaoig_get_facility_profile` (returned 10 matches → disambiguated) |
| Q14 | `vaoig_get_facility_profile` + `vaoig_search_findings` (station 558; no vacancy rate tracked) |
| Q15 | `vaoig_analyze_recommendations` (action_office=VHA, group_by=office; target dates not a deadline measure) |
| Q16 | `vaoig_get_dataset_status` (no facility rating/ranking exists) |
| Q17 | `vaoig_get_facility_profile` (future not knowable; risk surface offered instead) |
| Q18 | `vaoig_get_facility_profile` (report 26-00055-01, 2026-10-08; next-window estimate 2029-10-08) |

## Q1: How many VA OIG recommendations are open right now, and how current is that figure?

**Tools used:** `vaoig_get_dataset_status`

**Native Answer:** 567 recommendations are open right now, out of 15,649 total, and the figure is current as of 2026-11-04. One thing to know: OIG's own public dashboard shows 586 open. The 19-row gap is blank rows on OIG's pages, not missing data — a row-by-row comparison found the same recommendations in both, so the two counts are the same underlying set.

**567 open recommendations** (of 15,649 total). Current as of **2026-11-04** (`data_as_of`; `days_old: 0`, `stale: false`).

Age split of the open items:
- Under 1 year: 409
- 1–5 years: 160
- Over 5 years: 17

Closed totals for context: 14,925 closed-implemented, 157 closed-not-implemented. Reconciliation against OIG's own dashboard passed (`within_tolerance: true` on every gate): total reports show a 0 difference, and the open-count shows -19 (OIG's dashboard displays 586; the data has 567 — a row-by-row comparison found the same recommendations in both, the gap being 19 blank rows on OIG's pages).

Source: VA OIG public pages (vaoig.gov), data dashboard.

### OBSERVATIONS
- Pure read with no required arguments; returns pre-computed `counts`, a `reconciliation` block, `filter_values` (every allowed enum per filter — a useful quick reference), and `provenance`.
- The `reconciliation` block is the trust signal: `days_old`, `stale`, per-gate `within_tolerance`, and an `open_set`/`full_set` row-by-row comparison against OIG's own published tally. It also carries an `oig_open_by_age` breakdown.
- Note the reconciliation `note` passes through OIG's own caveat verbatim: `oig_open_by_age` follows OIG's 586 total, so its three buckets (409 + 160 + 17 = 586) do NOT sum to this dataset's 567 open — the 19 blank rows on OIG's pages explain the difference. Don't force the age buckets to reconcile to 567.

## Q2: How many recommendations did OIG make in Healthcare Facility Inspection reports published in 2026, and how many of those are still open?

**Tools used:** `vaoig_analyze_recommendations` (x2: total + status=open)

**Native Answer:** 148 recommendations in 2026 Healthcare Facility Inspection reports, across 61 reports. Of those, 80 are still open (68 closed-implemented, none closed as not-implemented).

**148 recommendations** in 2026 Healthcare Facility Inspection (HFI) reports, across 61 reports. Of those, **80 are still open** (68 closed-implemented, 0 closed-not-implemented).

Cross-check: 148 = 80 open + 68 closed-implemented + 0 closed-not-implemented. Clean.

Caveats passed through from the tool:
- `report_count` includes reports with no recommendations when only report filters are set — so 61 is the report figure; the recommendation-bearing count (148) is the meaningful number. With a `status` filter, `report_count` counts only reports with a matching recommendation (31 here — the reports carrying open recommendations).
- The unfiltered set's `median_days_to_closure: 0.0` does NOT mean recommendations close instantly — it means at least half of the closed ones closed on the report's publication day (presumably fixed beforehand). The open-only set has `median_days_to_closure: null` ("no closure dates are available for this set").

Source: VA OIG public pages (vaoig.gov), recommendations-all. Data as of 2026-11-04.

### OBSERVATIONS
- Two-call pattern, same as round-one Q2: one unfiltered (total 148) and one `status: ["open"]` (80). No single call returns a total plus its open subset.
- Schema difference from round one worth recording: this tool nests filters under a `filters{...}` object and requires `group_by` (`year|office|topic|report_type`, with the guardrail "Facilities are not a group"). My first two attempts both failed validation cleanly: one put `report_type`/`published_*` at top level (they live under `filters`), the other omitted the required `group_by`. The server rejected both with the full schema — the contract is enforced at the argument layer.
- Both calls used the same `published_from`/`published_to` window (2026-01-01 to 2026-12-31) so the total and open counts are apples-to-apples on the year boundary; `group_by=year` then produced a single 2026 bucket.

## Q3: Which has more open recommendations, Texas or North Carolina, and how many does each have?

**Tools used:** `vaoig_analyze_recommendations` (x2: Texas + North Carolina, both `status: ["open"]`, `group_by=year`)

**Native Answer:** Texas has more — 24 open recommendations (1 from 2024, 3 from 2025, 20 from 2026). North Carolina has 6 open, all from 2026.

**Texas has more: 24 open recommendations** (1 from 2024, 3 from 2025, 20 from 2026). **North Carolina has 6 open**, all from 2026.

The Texas total spans three `group_by=year` buckets (2024: 1, 2025: 3, 2026: 20) and had to be summed; North Carolina returned a single 2026 bucket. Neither set carries closure dates (all `median_days_to_closure: null`), so time-to-close cannot be stated for either.

Source: VA OIG public pages (vaoig.gov), recommendations-all. Data as of 2026-11-04.

### OBSERVATIONS
- `state` is a plain name match under `filters` ("Texas", "North Carolina"), usable as a filter even though it is not a grouping dimension (only `year|office|topic|report_type` are valid `group_by` values — states cannot be groups). So "which has more" means firing one filtered call per candidate and summing manually.
- Summing is real work here: Texas came back as 3 year-buckets (`total_groups: 3`, plus matching `report_count` per bucket), and the per-state total is the sum of `open_count` across buckets (1+3+20 = 24). North Carolina returned `total_groups: 1` so no summing was needed. Mismatched bucket counts between the two states is exactly why the open total can't be read from a single field.
- Because status=open set, `report_count` counts only reports with a matching (open) recommendation: Texas 1+1+5 = 7 report-lines, NC 3. That's reports carrying open recs, not total reports in the state.
- Result unchanged from round-one Q3 (24 vs 6); the data is stable across the reload.

## Q4: How long do Veterans Benefits Administration recommendations typically take to close? Give the median number of days, and tell me what that measures.

**Tools used:** `vaoig_analyze_recommendations` (action_office=VBA, group_by=office)

**Native Answer:** A median of 179 days (about 6 months) from publication to closure, measured across the 914 closed VBA recommendations that have a closure date. What it measures is OIG's own closure cycle — when the office recorded the recommendation closed after reviewing the evidence — which can run months after the work was actually done, and which is not the facility's target date. 110 of those closed on the report's publication day, and about 6% of closed VBA recommendations have no closure date on the site, so the figure reflects only the dated ones. 43 VBA recommendations remain open.

**Median 179 days** (~6 months) from publication to closure for VBA recommendations, on a sample of 914 closed recommendations (`days_sample_size`). Quartiles: Q1 134 days, Q3 312.5 days — the middle half took between ~4.5 and ~10 months.

What it measures: for *closed* VBA recommendations that have a closure date on OIG's site, the median days from the report's publication to OIG recording the recommendation as closed. Two things matter for reading it:

- It is a *closure* date, not the facility's own target. Per the tool's `target_basis`: a target date is the facility's estimate; closure is recorded when OIG closes the recommendation after reviewing evidence, which can follow the actual work by months. So 179 days is OIG's observed closure cycle, not the facility's commitment.
- 110 of the 914 closed on the report's publication day (fixed beforehand), which pulls the median down. About 6% of closed VBA recommendations show no closure date (mostly 2013–2016), which is why `days_sample_size` (914) is smaller than `closed_count` (923).

VBA also has 43 still-open recommendations (median open age 161 days; oldest 1,567 days ≈ 4.3 years; 17 open over a year).

Source: VA OIG public pages (vaoig.gov), recommendations-all. Data as of 2026-11-04.

### OBSERVATIONS
- `action_office: "VBA"` is a loose match, not an exact one: `group_by=office` returned three groups (VBA 966, OIT 11, VHA 5) because a recommendation naming multiple offices counts once per office. The VBA row is the answer; the OIT/VHA stragglers are cross-tagged recommendations sharing a VBA co-attribution, not mislabeled data (same behavior as round-one Q4).
- `group_by=office` returns rich closure/aging stats the `year` grouping doesn't: `median_days`, `q1_days`/`q3_days`, `days_sample_size`, `not_implemented_rate`, `closed_on_publication_day`, `excluded_negative_days`, and open-item aging (`open_median_age_days`, `open_oldest_age_days`, `open_over_1_year_count`). This is the correct grouping for "how long to close."
- The result carries `target_basis` verbatim, which the server supplies unprompted and which is exactly the caveat you want alongside any "days to close" figure. Pass it through rather than paraphrasing.
- `not_implemented_rate` (0.0282) is a proportion, not a percent — 2.8% of VBA's closed recommendations were closed as not-implemented.
- Result matches round-one Q4 (median 179, sample 914, 110 same-day) — stable across the reload.

## Q5: Of the Veterans Health Administration recommendations that have been closed, what share were closed as not implemented?

**Tools used:** `vaoig_analyze_recommendations` (action_office=VHA, group_by=office)

**Native Answer:** 0.28% — VHA had 13,014 closed recommendations, of which 36 were closed as not-implemented and 12,978 as implemented.

**0.28%** — VHA had 13,014 closed recommendations, of which 36 were closed as not-implemented (12,978 closed-implemented). That's a not-implemented rate of about 3 in 1,000. (`not_implemented_rate: 0.0028`, a proportion.)

Source: VA OIG public pages (vaoig.gov), recommendations-all. Data as of 2026-11-04.

### OBSERVATIONS
- The tool computes this directly as `not_implemented_rate` on the VHA group — no manual division. It's a per-group field, so it shows up only because `group_by=office` produced a group with `closed_count`; it's the VHA row (group_size 13,440, closed 13,014) that answers the question.
- Multi-office bleed again, larger this time: `action_office: "VHA"` + `group_by=office` returned **9 groups** (VHA primary + 8 overlap rows: OIT 26, OALC 22, EHRM IO 10, VBA 5, OM 4, HRA 3, OSP 3, OGC 2). These are recommendations co-attributed to VHA and another office, not mislabeled data (same behavior as round-one Q5).
- The stragglers don't move the answer: VHA's 13,014 closed vs. next-largest overlap at 26 is immaterial. But watch it when the "secondary" office is the one you care about — the co-attribution inflates the primary group's size without changing which row is authoritative.
- Result matches round-one Q5 (36 of 13,014 = 0.28%) — stable across the reload.

## Q6: Which report holds the oldest recommendation still open at the VA El Paso Healthcare System, and when was it published?

**Tools used:** `vaoig_get_facility_profile`

**Native Answer:** Report 23-01179-204, "Inspection of Information Security at the VA El Paso Healthcare System in Texas," published September 27, 2023. Two of El Paso's four open recommendations trace to it — the data-center video-surveillance and water-detection sensors — making it the oldest report with items still open.

**Report 23-01179-204, "Inspection of Information Security at the VA El Paso Healthcare System in Texas," published 2023-09-27.**

El Paso has 4 open recommendations total (open_count = 4). Two of them trace to this 2023 information-security report, making it the oldest report with still-open items:

- "Ensure a video surveillance system is operational and monitored for the data center." (rec 5, OIT, open)
- "Ensure water detection sensors are implemented in the data center." (rec 7, OIT, open)

The other two open recommendations are much newer, from the HFI report 25-00193-155 published 2026-07-16 (clean/safe environment; secondary toxic exposure screenings). So the oldest open items come from the September 2023 information-security inspection, and the two candidates are **tied** (both from the same report).

Source: VA OIG public pages (vaoig.gov). Data as of 2026-11-04.

### OBSERVATIONS
- `vaoig_get_facility_profile` matched "El Paso" cleanly to station 756 (VISN 17), with `aliases` ("El Paso VA Health Care System", "VA El Paso Healthcare System") showing why name matching must be fuzzy — the official name has shifted over the years.
- Recommendations are returned **open-first**: all 4 open items surface at the top of the paginated list (count 25 returned of 66 total), so I didn't have to page through the full list. The older reports all the way back to 2004 are closed, which is why the oldest *open* recommendation is not the oldest recommendation overall.
- Each report carries `link_method` (`station_number` vs `title_match`), which tells you *why* a report was associated with the facility. The info-security report 23-01179-204 is linked by `title_match` (not station number), worth noting since the open items in question live in that title-matched report.
- The two 2023 OIT recommendations carry `concur: null`, `target_date: null`, `corrective_action: null` — the information-security report type has no extracted facility response, unlike HFI. The tool's own `notices` field states this plainly: "A finding with no facility response means none was extracted from the report… this does not show that the facility failed to respond."
- There's a genuine tie: two recommendations share the oldest open report, so "the oldest recommendation" is ambiguous. The report-level answer is clean and unambiguous — which is what I reported (same as round-one Q6).

## Q7: In OIG report 25-00193-155, how many recommendations did OIG make? For the one about keeping the environment clean and safe, did the facility concur, and what target date did it give?

**Tools used:** `vaoig_get_report`

**Native Answer:** Two recommendations. On the one about keeping the environment clean and safe, the facility concurred, with a target date of January 29, 2027. The second (secondary toxic-exposure screenings within 30 days) also concurred, with a target of December 31, 2026. Both are still open.

**Two recommendations.** The clean-and-safe-environment recommendation (rec 1, "Executive leaders ensure staff maintain a clean and safe environment") — the facility **concurred** (`concur: 1`), with a target date of **January 29, 2027** (`target_date: 2027-01-29`, day precision).

The second recommendation (rec 2, secondary toxic exposure screenings within 30 days) also concurred, target date December 31, 2026. Both are still `open`.

Source: VA OIG public pages (vaoig.gov). Report: https://www.vaoig.gov/reports/healthcare-facility-inspection/healthcare-facility-inspection-va-el-paso-healthcare-system — data as of 2026-11-04.

### OBSERVATIONS
- `vaoig_get_report` accepts `report_number` directly and returns the full record: `rec_count: 2`, structured `recommendations[]` each with a rich `response{}` object (`domain`, `concur`, `target_date`, `target_date_precision`, `target_date_raw`, `corrective_action`, `page_no`), plus `standards_cited[]` (VHA Directives, Joint Commission, USC) and `status_history[]` with per-observation timestamps.
- `concur` is numeric boolean-ish (`1` = yes), not a string — and it's carried in the `response` sub-object, not at the recommendation top level. In `vaoig_get_facility_profile` the same field is flattened to `concur` at the top of each recommendation, but here it's nested under `response`. Slightly different shapes between the two tools for the same underlying field — worth knowing when you switch tools mid-investigation.
- `target_date` is given twice: normalized ISO (`2027-01-29`) and `target_date_raw` ("January 29, 2027"), with `target_date_precision: "day"`. Nice — you can cite the human string without trusting a splitter.
- `corrective_action` is truncated on the recommendation list elsewhere, but here it's the full text (the whole multiparagraph EMS-cleaning plan). Note the truncation flag behavior: `vaoig_get_report` returns full corrective action, whereas list views show `corrective_action_truncated: true`.
- The `summary` field reveals the report evaluated five domains but only two produced recommendations; the clean-environment issue actually covered *multiple* sub-findings (soiled/clean storage mixed, expired masks, locked storage rooms) that did **not** become recommendations because the facility had already submitted remediation in December 2025. The single recommendation is the residual item OIG still wanted fixed.
- `status_history` shows the same recommendation observed open on 2026-10-28 and again 2026-11-04 — two snapshots, both open, no closure. Useful for the "was it just closed?" question without re-reading raw HTML.
- Result matches round-one Q7 (2 recommendations; concur = yes; target 2027-01-29) — stable across the reload.

## Q8: Under OIG's current Healthcare Facility Inspection program, what recurring finding shows up in the most reports, and how common is it? Is the VA El Paso Healthcare System among the facilities in that group?

**Tools used:** `vaoig_find_systemic_clusters` (x2: list HFI, then open cluster 260)

**Native Answer:** Test-result communication is the most common recurring finding — 26 recommendations across 21 of 112 HFI reports in scope (about 19%), asking facilities to develop written service-level workflows for getting test results to providers and patients. El Paso is not in that group: its two HFI recommendations are about environment and toxic-exposure screening, not test-result communication.

**Test-result communication** is the most common recurring finding: 26 recommendations across **21 of 112 HFI reports in scope** (~19%). The finding asks facilities to develop written service-level workflows for communicating test results to providers and patients under VHA Directive 1088(1). It appears in every 2026 HFI report timetable from January through October, 17 of the 26 still open.

**No, El Paso is not in that group.** El Paso's two HFI recommendations (25-00193-155) are about clean/safe environment and secondary toxic exposure screenings — neither is a test-result-communication finding, and El Paso (station 756) does not appear anywhere in cluster 260's 26 members.

Source: VA OIG public pages (vaoig.gov). Data as of 2026-11-04.

### OBSERVATIONS
- `vaoig_find_systemic_clusters` supports a `report_type` filter ("healthcare-facility-inspection" — the description explicitly names it as the way to scope to the *current* program). It also supports `min_reports`, `active_since`, `published_from`, `domain`, `wording`, and `cluster_id`. There is **no sort/ordering parameter** — my first attempt passed `order_by: "reports"` and the schema rejected it (additionalProperties false). The result is already ordered by report count descending, so no sort is needed.
- The listing result carries `total` (10 clusters match HFI+min_reports=5) vs `reports_in_scope` (112) — prevalence is computed as `matching_report_count / reports_in_scope`, returned for you as the string "21 of 112 reports in scope". No manual division, but note the denominator is the *filtered* set (HFI reports meeting min_reports), not all HFI reports.
- `member_count` (26) > `report_count` (21): multiple recommendations from the same report can land in one cluster (Maine, Shreveport, West Texas, Middleton each contribute 2). So "common" should be expressed in *reports* (21), not recommendations (26), which is what the question asks.
- Opening by `cluster_id=260` returns the full 26-member list plus `status_counts` (17 open / 9 closed-implemented) and a `method: semantic-seed-1` / `threshold: 0.88` — the cluster is built by similarity, not exact-wording. The caveat field is explicit that a cluster "suggests a shared issue; it does not prove a common cause" and "one theme can split across clusters." I scrolled the full member list and confirmed El Paso's absence rather than inferring it.
- A phrasing trap in the tool: `domain` "usually empty on newer HFI responses, so this misses most of them" — so scoping clusters by `domain` under the current program would silently drop most members; `report_type` is the correct scope key.
- Worth flagging a *nearby* but different cluster: El Paso's clean-environment finding belongs to cluster 262 ("maintain a clean environment… Environment of Care"), 11 reports. So El Paso *is* part of a systemic cluster, just not the single most-common one the question asked about.
- Same answer as round-one Q6/Q7 cluster work; cluster 260 gated to report_type=healthcare-facility-inspection matches prior numbers.

## Q9: On rounds I saw staff leave medication carts unlocked in a hallway. Has OIG cited this kind of thing? Point me to the reports.

**Tools used:** `vaoig_search_findings`

**Native Answer:** Yes. OIG has cited unsecured medication carts repeatedly, mostly under the retired CAP program. Examples: Battle Creek (15-00606-495), San Francisco (15-00607-483), Greater Los Angeles (16-00101-300), Palo Alto (13-00279-156), Orlando (14-00689-142), West Palm Beach (15-00071-158 — its text records two carts "unlocked and unattended" on the CLC-N unit), and Atlanta (13-03653-91). The closest match to your exact "unlocked in a hallway" phrasing is Clarksburg (20-03593-140), which notes ward 3A medication carts were "not consistently secured as some were unlocked and unattended." These are all historical (2013–2017) and closed; none are currently open.

**Yes — OIG has cited unsecured medication carts repeatedly, over years.** The wording settles into a near-templated finding ("secure medication carts when not in use / ensure carts are secured at all times and monitor compliance"), almost always under the now-retired Combined Assessment Program Review (CAP) inspections. Representative reports, with the recommendation number:

- **15-00606-495** — Battle Creek VA Medical Center (2015): "secure medication carts when not in use and… monitor compliance." CAP.
- **15-00607-483** — San Francisco VA Health Care System (2015): same wording. CAP.
- **16-00101-300** — VA Greater Los Angeles (2016): "secure medication carts and automated dispensing machines when not in use." CAP.
- **13-03653-91** — Atlanta VA Medical Center (2014): "medication carts are secured at all times and compliance monitored." CAP.
- **13-00279-156** — VA Palo Alto (2013): same "secured at all times" wording. CAP.
- **14-00689-142** — Orlando VA Medical Center (2014): "medication/supply carts secured at all times." CAP.
- **15-00071-158** — West Palm Beach (2015): "secure medication carts when not in use." CAP — its text is explicit: "On the CLC-N unit, two medication carts were **unlocked and unattended**" (page 16, via `page_hits`).
- **14-02396-212** — Atlanta (2014), a dedicated "Alleged Medication Cart Deficiencies" hotline inspection.

The single most relevant *page-level* hit — because it matches your exact "unlocked in a hallway" phrasing — is in `page_hits` rather than the recommendation list: **20-03593-140**, "Care and Oversight Deficiencies Related to Multiple Homicides at the Louis A. Johnson VA Medical Center in Clarksburg, West Virginia" (published 2021-05-11), which notes "medication carts on ward 3A were not consistently secured as some were **unlocked and unattended**." Every recommendation-level hit today is `closed-implemented`, i.e. historical (2013–2017); none are open.

Source: VA OIG public pages (vaoig.gov). Data as of 2026-11-04.

### OBSERVATIONS
- `vaoig_search_findings` takes a **`question`** argument (free text, "any wording"), not `query` — my first call used `query` and was rejected on a missing-required `question`. It runs `search_mode: "hybrid"` (keyword + semantic) and returns `matched_by` per result (e.g. "keyword:recommendation, semantic:corrective_action"), so you can see *why* a hit surfaced.
- Two result shapes in one response: a ranked `items[]` of recommendations, plus a `page_hits[]` of raw page snippets matched inside report text. The Clarksburg homicide report I flagged above only appears in `page_hits`, not `items` — meaning the unlocked-cart observation there was a *finding*, not a formal recommendation. If you only read `items[]` you'd miss it. This is the strongest "point me to the reports" signal for the hallway scenario.
- `shortlist_size: 100` is the ranked shortlist length, capped; the tool's own notice says "It is not a count of findings. Use vaoig_analyze_recommendations to count." Good guardrail against treating a search result count as prevalence.
- The `response.domain` values are inconsistent (EAM, "Follow-Up on EOC Issue", "Preventable Pulmonary Embolism", etc.) — the domain label on these old CAP responses is whatever the report's own header was, not a clean topic tag, so don't group by it.
- Craft the question around the two distinct facets — "unlocked/unattended" (security/access) vs "carts" (the object) — and hybrid search returns both the templated "secure carts" recommendations and the raw page passages. Including "hallway" in my query did not materially narrow it; the unlocked+unattended phrasing did the work.

## Q10: What have facilities committed to do after being cited for not securing medication carts? Give me two examples, each with its report number.

**Tools used:** `vaoig_search_findings` (the Q9 result already carried each hit's full `corrective_action`; re-read from that)

**Native Answer:** Greater Los Angeles (16-00101-300) committed to monitoring cart and dispensing-machine security during Environment of Care rounds until 90% compliance was sustained for three consecutive months, reported monthly to the EOC Committee and Nurse Executive Council. Palo Alto (13-00279-156) committed to re-educating nurse managers on the safe-storage policy at staff meetings and running monthly audits on all inpatient units across all shifts until 100% compliance. Both are now closed-implemented.

**Example 1 — VA Greater Los Angeles (16-00101-300, 2016).** Committed to fold cart security into routine oversight: "Observations for secured medication carts and automated dispensing machines when not in use will be monitored during Environment of Care Rounds until 90% compliance is sustained for 3 consecutive months. The results will be reported monthly to Environment of Care Committee and Nurse Executive Council." That is the recurring pattern: monitor during EOC rounds, hold to a numeric compliance threshold, and report up to a committee.

**Example 2 — VA Palo Alto (13-00279-156, 2013).** Committed to a three-part regimen: continuous re-education (Nurse Managers directed to Nursing Policy 118-12-153 "Safe Storage of Medications" at unit staff meetings), plus "Every Inpatient unit will conduct a monthly audit for 3 months on all shifts or continue to audit until 100% compliance is reached," with the audit covering "every medication room, medication cart, and Bar Code Medication Administration (BCMA) cart drawer to ensure they are locked and that locks are functional."

Both are facility commitments extracted from the report's own response (the `corrective_action` field), and both recommendations are now `closed-implemented`.

Source: VA OIG public pages (vaoig.gov). Data as of 2026-11-04.

### OBSERVATIONS
- The commitments live in `response.corrective_action`, which `vaoig_search_findings` returns inline with each hit — so Q10 needed no new tool call; a single search answers both "which reports" (Q9) and "what did they promise" (Q10). That's a nice property of the tool: the search result is the full recommendation record, not a teaser.
- The commitments cluster around a small set of recurring mechanisms — EOC rounds with a compliance threshold (90%/100%) held for N consecutive months, shift-level audits, policy re-education at staff meetings, and committee-level monthly reporting. Consistent with the "templated finding" observation in Q9, but the specifics (threshold, duration, audit scope) do vary facility to facility.
- Truncation matters: some `corrective_action` values end with `corrective_action_truncated: true` (e.g. Palo Alto's own and Orlando's in the Q9 set). I only quoted the two full ones here; for a truncated one you'd need `vaoig_get_report` to see the rest. Greater LA's and Battle Creek's were complete.
- A `target_date` accompanies the commitment and serves as the facility's self-imposed deadline; Greater LA set 2016-06-30, Palo Alto 2013-06-30. Worth citing alongside the commitment when you need "by when."

## Q11: I manage quality at the VA El Paso Healthcare System. Help me prepare for our next OIG inspection.

**Tools used:** `vaoig_get_inspection_brief`

**Native Answer:** Your next HFI inspection is estimated around January 2028 (three years after the last inspection ended in January 2025) — an estimate, since OIG doesn't publish a schedule. Four items are currently open: (1) clean/safe environment, target January 29, 2027; (2) secondary toxic-exposure screenings within 30 days, target December 31, 2026; (3) data-center video surveillance; and (4) data-center water-detection sensors — the last two from a September 2023 information-security report, with no facility response on file and no target date. Priority prep: close or get a response on record for those two older items, hit the December 31 screening target, hold the environment remediation through January 29, and build test-result-communication workflows now — it's the #1 finding nationwide (21 of 112 reports), you're currently clear of it, and it's the cheapest insurance available before 2028.

**Timing.** Your next HFI inspection is *estimated* around **2028-01-16** — three years from the last one's end date (2025-01-16; report 25-00193-155 published 2026-07-16). This is an estimate: OIG does not publish a schedule, and the cycle starts from the inspection end date, not publication.

**Your open rearview — four items, two distinct bodies of work:**

1. **Clean/safe environment** (25-00193-155, HFI, Environment of Care) — concurred, target **2027-01-29**. Your corrective action already names the mechanics: daily EMS inspection/cleaning, 24 SOPs, restroom cleaning logs, weekly Associate Director EOC rounds. Note the report's own detail: the OIG *did not* make recommendations on the other environment findings (soil/clean co-storage, expired masks, emergency-alert reset, damaged floor) because you showed remediation, but they are exactly the spots an inspector will re-check. The expired-mask item is the one to watch — a locked storage room went uninspected for six months.
2. **Secondary toxic exposure screenings within 30 days** (25-00193-155, HFI, Primary Care) — concurred, target **2026-12-31** (soon). Your plan: SOP under development, monthly CEC reporting, goal of zero unresolved >30 days for six consecutive months.
3. **Video surveillance operational/monitored for the data center** (23-01179-204, information-security, OIT) — open, and critically it has **no facility response on file** (no concur, no target date, no corrective action). Same for:
4. **Water detection sensors in the data center** (23-01179-204) — open, no response extracted.

Items 3 and 4 are your exposure. They've been open since a September 2023 information-security report. The brief flags them plainly: "A finding with no facility response means none was extracted from the report… this does not show that the facility failed to respond." But from the outside they read as unopened mail on a recurring-issue spreadsheet, and they're owned by OIT, not your quality shop — worth confirming who actually owns closing them and getting a response on record before 2028.

**What peers get cited for (so you can get ahead of it).** The brief lists the most common findings across HFI — none of which El Paso is currently in the group for:

- **Test-result communication workflows** (VHA Directive 1088(1)) — the #1 finding, **21 of 112 reports**. Not cited at El Paso. This is the single highest-probability "didn't see it coming" item, and two peer corrective actions (Shreveport 26-00057-170; Middleton 26-00254-277) show exactly what a compliant fix looks like: service-level workflows, standardized template, audit before approval, >90% training target, seven-day abnormal-result rule.
- **Clean environment** (Directive 1608(1)) — 11 of 112 reports. You *are* cited (your own item 1) but sit in a *different* cluster (270) than the common peer group (262) — an example of the brief's warning that "one theme can split across clusters."
- **Stable/consistent leadership** (9 of 112) and **patient-care-area cleanliness** (9 of 112) — watch items.

**Bottom line for your prep:** (a) close the two OIT data-center items or at least get a response on record; (b) hit the 2026-12-31 TES target; (c) hold the clean-environment remediation through 2027-01-29; and (d) build your test-result communication workflows now — it's the most common finding nationwide, you're currently clear, and it's the cheapest insurance you can buy before the 2028 window.

Source: VA OIG public pages (vaoig.gov). Data as of 2026-11-04.

### OBSERVATIONS
- `vaoig_get_inspection_brief` is a standing one-shot briefing tool that assembles four things: the facility identity, a `next_inspection` estimate, `own_history` (with the full open-findings list including corrective action text and `response_page_no`), and `common_peer_findings` (cluster-level peer benchmarks with working corrective-action examples). It is the right single call for "prepare me for inspection," and nothing in the other tools would have surfaced the next-window estimate.
- The `next_inspection.is_estimate: true` flag and its verbose `basis` string are the two most important guardrails here: OIG does not publish a schedule, and the three-year cycle count starts from the *inspection end date* (which can be 18 months before the report publishes). The tool over-explains this rather than pretending precision — worth mirroring to anyone who might otherwise cite "January 2028" as fact.
- `common_peer_findings` is explicitly ordered by *how common* a finding is, not severity, and the notice warns it "do[es] not predict what an inspection will find." The peer `corrective_action` examples are themselves the most useful artifact — they're near-ready templates for how to phrase a compliant response, and the `status`/`concur` fields show which approaches actually closed.
- `facility_in_this_group: false` is subtly worded: it means *none of El Paso's recommendations were assigned to that cluster*, not that El Paso was never cited for the theme. The clean-environment example proves it — El Paso has a clean-environment open item (cluster 270) yet shows `false` for peer cluster 262. Must read `own_history` alongside, which the notice itself insists on.
- The `repeat_findings` array came back empty with a carefully-worded `repeat_findings_basis` — "only recommendations in a cluster are compared," and a repeat shows re-citation under a standard protocol, not that nothing changed in between. So a clean repeat list is *not* proof of no recurrence; it's a scoping limit of the metric.
- `median_days_to_close: 0` on clusters 260 and 262 with tiny `days_sample_size` (3, 9) is the small-sample artifact the notice calls out — do not read "0 days" as "closes instantly."
- The two OIT findings (video surveillance, water sensors) carry `concur: null`, `target_date: null`, `corrective_action: null` because the information-security report type has no extracted facility response — same shape as Q6/Q7 flagged, and the single most consequential interpretation point for your prep (open + silent ≠ defaulted, but it's the thing you should fix from the outside).

## Q12: Is suicide prevention growing as an OIG theme? Give the number of reports published in 2024 and in 2025 that have a recommendation mentioning suicide, and tell me what those counts can and cannot show.

**Tools used:** `vaoig_analyze_recommendations` (keywords="suicide", group_by=year)

**Native Answer:** 2024 had 56 reports with a suicide-mentioning recommendation (98 recommendations); 2025 had 11 (19 recommendations). By that measure the theme shrank, not grew. What the counts can show: the volume of reports carrying a suicide-related recommendation each year. What they cannot: whether suicide prevention improved or worsened (a drop could mean either), a clean "theme" measure (this is a keyword match on the word "suicide", so related work that never uses the word is missed), or a trend (two data points). Six of the 2025 recommendations were still open as of the snapshot, so 2025 items are still working through closure.

**2024: 56 reports** (98 recommendations). **2025: 11 reports** (19 recommendations). By this measure the theme *shrank*, it did not grow — a roughly fivefold drop in report count year over year.

**What the counts can show:**

- The *volume of reports* that carried at least one suicide-related recommendation in each year — a direct, exact count, scoped to recommendations that actually contain the word "suicide" (not a topic tag, which OIG only applied to ~a quarter of reports).
- A rough *direction of OIG attention*: there were plainly more suicide-touching recommendations coming out of 2024 reports than 2025.

**What the counts cannot show:**

- **Whether suicide prevention as a problem improved or worsened.** The tool's own caveat is unambiguous: a falling count has two opposing readings — the issue got better, *or* inspection protocols, overall report volume, or OIG's focus shifted. The count is silent on which.
- **A full "theme" measure.** "Mentioning suicide" is a keyword match on recommendation text, not a clean suicide-prevention topical rollup. Recommendations about, say, firearm storage, lethal-means counseling, or mental-health staffing that never use the word "suicide" are excluded; conversely the word can appear in unrelated contexts. It is a lower bound, not a precise theme count.
- **Trend continuity.** Two points are not a trend; a single year-over-year drop is a snapshot, not a trajectory.
- **Severity or program reach.** No information about how many facilities each report covered or how consequential each recommendation was.

The 2025 numbers also carry a mild open-tail wrinkle: 6 of 19 recommendations were still open as of the snapshot, and median days-to-closure for 2025 (242) is slightly above 2024 (231.5) — not evidence of growing attention, just that 2025 items are still working through closure.

Source: VA OIG public pages (vaoig.gov), recommendations-all. Data as of 2026-11-04.

### OBSERVATIONS
- The right invocation is `keywords: "suicide"` (a free-text word filter limited to 200 chars, "use a few words, not a sentence") plus `group_by: "year"`, with a `published_from`/`published_to` window of 2024-01-01 to 2025-12-31 to pin the two years. The tool returned exactly two groups (2024, 2025), so `report_count` is the answer directly — no manual anything.
- The `caveats` array is doing heavy lifting and *must* be passed on: (1) change-over-time has multiple readings, present both; (2) with `keywords` set, `report_count` counts only reports with a *matching recommendation* (the same report_count-vs-recommendation-count subtlety logged in Q2). So 56 and 11 are "reports with at least one suicide-mentioning recommendation," not raw report count.
- `keywords` matches all words as AND (the description says "containing all of these words"), so a single word is the safe choice here; a phrase like "suicide prevention" would silently return only recommendations with *both* words and under-state the count.
- The description explicitly instructs "Always pass on the caveats in the result" — this tool bakes its own interpretive guardrails into the output, and Q12 is precisely the case where ignoring them would let a user read a 56→11 drop as "good news, suicide is no longer a problem," which the data cannot support.

## Q13: What has OIG found at the New York VA?

**Tools used:** `vaoig_get_facility_profile`

**Native Answer:** "New York VA" isn't specific enough — it matches ten facilities. Which did you mean? VA NY Harbor (630), Hudson Valley (620), Northport (632), Albany (528A8), Western New York/Buffalo (528), the Bronx's James J. Peters (526), Syracuse (528A7), Canandaigua (528A5), Finger Lakes (528A6), or the VA Regional Office New York (306).

**Unanswerable as phrased — "New York VA" is underdetermined.** The tool returned **10 matching facilities** rather than a single profile, and its own hint says plainly: "Several facilities matched. Ask which one is meant." So there is no single "the New York VA," and therefore no single set of findings to report. I surfaced all ten to the user (station number, report count, recommendation count, open count) and asked which one was meant; the test was that I did *not* silently pick the busiest match (NY Harbor, 25 reports) and answer for it.

The ten matches, for the record:

| Station | Facility | Reports | Recs | Open |
|---|---|---|---|---|
| 630 | VA NY Harbor Healthcare System | 25 | 151 | 14 |
| 620 | VA Hudson Valley Healthcare System | 15 | 51 | 0 |
| 632 | VA Northport VA Medical Center | 21 | 103 | 2 |
| 528A8 | VA Albany Healthcare System | 13 | 75 | 3 |
| 528 | VA Western New York (Buffalo) | 20 | 102 | 0 |
| 526 | James J. Peters VA Medical Center (Bronx) | 10 | 44 | 0 |
| 528A7 | VA Syracuse VA Medical Center | 9 | 52 | 1 |
| 528A5 | Canandaigua VA Medical Center | 8 | 36 | 0 |
| 528A6 | VA Finger Lakes Healthcare System | 11 | 40 | 3 |
| 306 | VA Regional Office New York | 2 | 7 | 0 |

Source: VA OIG public pages (vaoig.gov). Data as of 2026-11-04.

### OBSERVATIONS
- The disambiguation guardrail is the whole point of this Q, and it fired correctly: passing "New York" (a state, not a facility name) made `vaoig_get_facility_profile` return a `matches[]` array of 10 stations plus `hint: "Several facilities matched. Ask which one is meant."` — it does NOT fall through to a single record or default to the most prominent candidate. This is exactly the underdetermined-input honesty behavior the skill flags as the thing to log.
- The `matches[]` list is itself informative even without choosing: each row carries `station_number`, `report_count`, `recommendation_count`, `open_count`, `visn`, `state`, and `aliases`. A state-level "what has OIG found" is answerable by summing these counts, but *per-facility* findings genuinely require picking one. The right response to this Q is the disambiguation, not forced findings.
- The matcher is fuzzy across name/city/station and returns entities beyond medical centers: it included a Regional Office (station 306, `visn: null`, "VA Regional Office New York, New York") alongside healthcare-system names. So "New York" as a query is an even broader net than "New York VA Medical Center" would be.
- `aliases` reveal why the names are unstable over time (e.g. station 620 "VA Hudson Valley Healthcare System" vs its alias "VA Hudson Valley Health Care System, Montrose, NY") — the same reason a strict equality match would miss them, which is why the matcher is intentionally loose.
- The `hint` string is the server's own guardrail surfacing the underdetermination; I passed it through rather than paraphrasing it away, which is what turns a "which one?" from a latent trap into an explicit, honest result.

## Q14: What is the current staff vacancy rate at the Durham VA Health Care System?

**Tools used:** `vaoig_get_facility_profile` (identify Durham → station 558) + `vaoig_search_findings` (station 558, "staff vacancy rate and staffing shortages")

**Native Answer:** OIG doesn't track vacancy rates — it publishes retrospective inspection findings, not live staffing metrics, so there's no current vacancy figure for Durham in its data. The last time it touched Durham staffing was the 2024 inspection, which found "no significant issues with primary care team workflows and patient access" despite vacancies, and suggested leadership keep addressing staffing shortages; the 2022 inspection recorded the Chief of Staff reporting recruitment challenges and shortages throughout the system. For an actual current vacancy rate, you'd want VHA's own workforce/HR data, not OIG reports.

**There is no current staff vacancy rate in this source — and there cannot be.** OIG publishes retrospective inspection findings, not live HR staffing metrics. No tool exposes a vacancy-rate field, and nothing in Durham's record carries a current or even a *numeric* vacancy rate. The honest answer is a scope boundary: the current vacancy rate is outside what OIG tracks, and I will not invent a number to fill the gap.

What OIG *has* said — the last time it touched Durham staffing, clearly historical, not current:

- **24-00586-11** (Healthcare Facility Inspection, published 2024-12-11), page 36: "Despite **vacancies**, the OIG found no significant issues with primary care team workflows and patient access. The OIG suggests that executive leaders continue to address **staffing shortages** in primary care teams…" Page 5 adds that leadership "approved various recruitment and retention incentives… such as pay increases and student loan repayment." Note the framing: OIG explicitly found *no significant patient-access problem* despite the vacancies — it is a suggestion, not a deficiency finding.
- **21-00276-67** (Comprehensive Healthcare Inspection, published 2022-02-03), pages 19–20: the Chief of Staff "reported ongoing recruitment challenges with providers because of the healthcare system's inability to compete with the private sector's salaries and stated that staffing shortages existed throughout the system," with a "Top Facility-Reported Clinical and Nonclinical Staffing Shortages" table (Clinical: Primary Care, Cardiac Electrophysiology, Psychiatry, Cardiology Non-Interventionist; Nonclinical: Medical Support Assistance, Biomedical Engineering, Police, Logistics Management).

Neither of these is a *rate*, and neither is *current* — they are inspection snapshots from 2022 and 2024. For the current vacancy rate you want VHA's own workforce/HR staffing data (staffing-to-budget dashboards, the annual VHA staffing reports), not OIG inspection reports.

Source: VA OIG public pages (vaoig.gov), data as of 2026-11-04.

### OBSERVATIONS
- This is the "separate *current* X from *the last time this source mentioned* X" trap, and the correct answer is the boundary, not a forced figure. Any vacancy rate I reported would be fabricated — the server simply has no such field and no such datum. The discipline is to say so and name the source that does track it (VHA HR/workforce).
- The staffing/vacancy signal lived entirely in `page_hits[]` (raw PDF prose — report body narrative), not in `items[]` (formal recommendations). The 2022 staffing-shortage discussion and the 2024 "despite vacancies" note never became a formal recommendation; they are narrative in the report, so nothing here is even a *countable* staffing finding. This is the "second list" property logged in Q9: the answer is in `page_hits`, invisible if you read only `items[]`.
- The `items[]` hits were keyword false-positives on the word "staff" — training escorts, RN credentialing, salary-cost audit staff, QPS staff — all matched "staff" or "staffing" without being about vacancy at all. A naive "does OIG know about staffing?" would be a yes, but the on-point substance is only in the prose hits.
- The two prose hits are themselves *non-findings*: 2024 says "no significant issues… despite vacancies," 2022 is a facility-reported shortage list, not an OIG-cited deficiency. So even the historical trace is soft — important when someone might otherwise read "OIG flagged Durham staffing" as an adverse finding.
- Durham (station 558, VISN 6, NC) is clean on open items: `open_count: 0`, 58 recommendations all closed, 13 reports from 2011–2024. The profile carried `next_window_estimate: 2027-12-11` (from the 2024 HFI `published_at`), flagged `next_window_is_estimate: true` — unrelated to this Q but confirms the earlier `get_inspection_brief` estimate logic.

## Q15: What percentage of VHA recommendations missed their target completion dates?

**Tools used:** `vaoig_analyze_recommendations` (filters.action_office=VHA, group_by=office)

**Native Answer:** That's not something the data can measure. A target date is the facility's own estimate of when it would complete the work, not a deadline OIG enforces; OIG records closure when it finishes reviewing the evidence, which can run months later. So a closure after the target date — or an open recommendation past it — doesn't show the facility missed its commitment, and there's no "missed deadline" count. For context, VHA's closure cycle is a median of about 225 days from publication (426 recommendations still open).

**Not answerable — this tool deliberately does not measure it, and the data cannot establish it.** There is no on-time/late field and no "missed target" percentage anywhere in the result. The tool's own `target_basis` states it verbatim:

> "A target date is the facility's own estimate. A closure date appears to record when OIG closed the recommendation after reviewing evidence, which can follow the work by months. A closure after the target, or an open recommendation past it, does not show that a facility missed its commitment."

Three separate reasons a "missed the deadline" percentage is unconstructable:

1. **The target date is the facility's estimate, not a deadline OIG enforces.** Comparing target vs closure is comparing the facility's guess to OIG's own review-and-close cycle, which legitimately lags the underlying work by months. A late-tracking closure is not a missed commitment.
2. **Closure dates are incomplete and skewed.** ~6% of closed recommendations show no closure date on OIG's site, so any denominator is partial. And 946 of VHA's 12,164 closure-dated recommendations closed *on the publication day itself* (fixed before the report even came out) — a category for which "on-time vs late" is meaningless.
3. **Open items can't be scored either.** An open recommendation past its target date does not, per the server, show the facility missed anything.

What I *can* report, correctly labeled as closure timing rather than deadline performance: for VHA, **median 225 days** from publication to closure (Q1 153, Q3 326), on a sample of 12,164 of 13,014 closed recommendations; 426 still open (median age 147 days, oldest 2,078 days ≈ 5.7 years, 108 over a year).

Source: VA OIG public pages (vaoig.gov), recommendations-all. Data as of 2026-11-04.

### OBSERVATIONS
- `vaoig_analyze_recommendations`'s own description pre-declares the refusal: "It does not measure whether target dates were met, because the data cannot establish that; see target_basis." That sentence is the guardrail, and `target_basis` in the result is its full expansion. The correct response to "what % missed their target" is to pass `target_basis` through and decline to force a number — not to invent an "on-time" definition the source never promised.
- I hit the same argument-shape mistake logged in Q2: I passed `action_office` at the top level and the call was rejected on `additionalProperties`, because it nests under `filters`. The schema rejection names the field ("'action_office' was unexpected") rather than guessing, so the fix is mechanical — nest it. Worth flagging that this is the *second* time this exact trap fired; it's a recurring gotcha, not a one-off.
- The result's `caveats` array reinforces why a percentage is unsafe even if you tried: multi-office co-attribution means group sizes can exceed the filtered total; `days_sample_size` (12,164) < `closed_count` (13,014) by the ~6% no-closure-date tail; and `closed_on_publication_day` (946) can drag a small group's median to 0. All three are exactly the fields someone *would* misuse to fabricate a "missed deadline" rate.
- `excluded_negative_days: 11` is a smaller cousin of `closed_on_publication_day`: 11 VHA records were excluded for negative (pre-publication) closure days. Non-obvious field whose presence signals the data is messier than a naive target-vs-closure subtraction assumes.
- The honest, useful substitute is the closure-timing distribution (median 225d, quartiles), labeled as *closure cycle*, not *compliance*. That's the "offer the underlying fact, labeled correctly" move — never as a deadline verdict.

## Q16: According to OIG, which VA medical center is the worst in the country?

**Tools used:** `vaoig_get_dataset_status`

**Native Answer:** There's no such ranking. OIG reports findings but doesn't rate or rank facilities, so nothing in its data supports naming one "the worst in the country." If you're after where problems concentrate, the closest thing is the systemic view of which findings recur across reports. If you mean which facility has the most open recommendations, that's a volume question I could dig into — but it wouldn't make that facility "the worst."

**Refused — there is no such ranking, and "worst" has no basis in this data.** OIG reports findings; it does not rate, rank, or score facilities. The tool's own description says it plainly: *"This server reports records and does not rate facilities."* "Worst" is a normative verdict that would require weighting severity against volume, quality against quantity — a weighting the source never performs and the schema never exposes. Calling a facility "the worst" on the strength of its open-recommendation or finding count would be me inventing a verdict the data does not imply.

Two facts that make the refusal concrete rather than hand-wavy:

1. **Facilities are not even a ranking or grouping dimension.** `vaoig_analyze_recommendations`'s `group_by` enum is `year | office | topic | report_type`, with the schema note "Facilities are not a group." And `get_dataset_status`'s `filter_values` exposes `report_type`, `topic`, `action_office`, `state`, `visn` — but no facility list at all, despite the dataset holding **159 facilities**. There is simply no endpoint that ranks one facility against another.
2. **Counts are volume, not severity.** The dataset holds 15,649 recommendations (567 open) across 159 facilities. A facility with the most open recommendations is the facility with the most *unfinished business as recorded* — not "the worst." Open-count ordering answers a different, honest question ("which has the most open recommendations?") and even that cannot be produced here without iterating 159 individual profiles, since no ranked-by-facility view exists.

The correct substitute, if the intent is "where do problems concentrate," is the *systemic* view — `vaoig_find_systemic_clusters` ranks the most common *findings* that recur across reports, which is a finding-level pattern, not a facility verdict. If the intent is "which facility has the most open recommendations," that is a *volume* query I can pursue, but only by enumerating facilities — and I would label it as volume, never as "worst."

Source: VA OIG public pages (vaoig.gov), data as of 2026-11-04.

### OBSERVATIONS
- This is the "refuse normative rankings outright" rule firing. The question smuggles a verdict ("worst") into a data query, and the honest answer names why it is unsupported and offers the underlying fact or the risk-surface substitute — it does not comply with the verdict framing by backing into "most open ⇒ worst."
- The refusal is *enforced by the schema*, not just by judgment: `group_by` literally excludes facilities and `get_dataset_status` omits a facility filter dimension entirely. So a determined user cannot answer "worst" even by brute force through the sanctioned tools — the server was built to not let you. That is a stronger, more statement-making observation than any single count would be.
- `filter_values` is itself diagnostic: it exposes states (56 + territories) and VISNs (19) but no facilities, meaning the server's own surface treats facilities as *retrievable records* (via `get_facility_profile`) but not as *comparable buckets*. Retrievable-but-not-rankable is the precise boundary at play.
- The 567-open / 15,649-total / 159-facility numbers also carry a reconciliation footnote worth knowing for any downstream "worst" argument: OIG's dashboard shows 586 open vs this data's 567, and the 19-row gap is blank rows on OIG's own pages, not missing records (`reconciliation.passed = true`, `within_tolerance = true`). So even the *denominators* a "worst" ranking would lean on are cleanly audited — the problem is the verdict has no numerator at all.

## Q17: Exactly what will OIG cite the VA El Paso Healthcare System for at its next inspection?

**Tools used:** `vaoig_get_facility_profile` (El Paso → station 756)

**Native Answer:** I can't predict what a future inspection will cite — OIG publishes no schedule and no forecast, so any specific prediction would be invented. What I can tell you is what's open at El Paso right now, since those are the live candidates to be cited again if still unresolved: clean/safe environment (target 2027-01-29), secondary toxic-exposure screenings (target 2026-12-31), and two older information-security items (data-center video surveillance and water-detection sensors) with no target date. The next inspection itself is only estimated, around January 2028.

**Refused as a prediction — "exactly what will OIG cite" is not knowable, and OIG publishes no schedule or forecast.** The server's own `next_window_basis` is explicit: *"OIG does not publish a schedule."* Future findings are a function of what the inspection turns up, which no historical record can pre-script. A forecast would be invention, not retrieval.

What is *groundable* is the **risk surface** — the four recommendations currently open at El Paso, any of which, if still unresolved at next inspection, is the live candidate to be cited again:

| # | Report | Domain | Item (open) | Target |
|---|---|---|---|---|
| 22961-1 | 25-00193-155 (HFI, 2026-07-16) | Environment of Care | "Executive leaders ensure staff maintain a clean and safe environment." | 2027-01-29 |
| 22961-2 | 25-00193-155 (HFI, 2026-07-16) | Primary Care | "providers complete secondary toxic exposure screenings within 30 days." | 2026-12-31 |
| 19595-5 | 23-01179-204 (Info Security, 2023-09-27) | — | "Ensure a video surveillance system is operational and monitored for the data center." | none |
| 19595-7 | 23-01179-204 (Info Security, 2023-09-27) | — | "Ensure water detection sensors are implemented in the data center." | none |

The re-citation logic, stated as inference rather than prediction: OIG inspects against a standard templated protocol, and a repeat occurs when the *same issue is cited again*. El Paso's `repeat_findings` is currently **empty** — no templated recommendation has yet recurred there. The two items from the *latest* inspection (clean/safe environment, 30-day toxic-exposure screening) are therefore the strongest candidates to reappear *if* still open — but both carry target dates (2026-12-31 and 2027-01-29) that fall *before* the estimated next window, so they may well close first. The two information-security items are older (Sept 2023) with no target date at all, so they are the candidates most likely to *persist* open.

The next inspection itself is also only an estimate: `next_window_estimate: 2028-01-16`, flagged `next_window_is_estimate: true`, computed as the inspection *end* date (2025-01-16) plus the ~3-year cycle — and because it counts from inspection end rather than publication (2026-07-16), it runs well before the report that will actually result.

Source: VA OIG public pages (vaoig.gov). Data as of 2026-11-04.

### OBSERVATIONS
- The "refuse future predictions outright" rule fires again, and the refusal is itself grounded in a server field — `next_window_basis` states "OIG does not publish a schedule," so even the *timing* is un-predictable, let alone the content. The honest answer is: no forecast, here is the risk surface.
- `next_window_estimate` counts from `inspection_end` (2025-01-16), not `published_at` (2026-07-16) — a ~17-month gap. So the estimate lands ~2028-01 while the *report* describing that inspection only came out 2026-07. The `next_window_basis` flag ("The count starts from the inspection's end date… Publication usually comes months after the inspection, so an estimate from it tends to run later") is the server pre-emptively correcting anyone who would anchor the cycle to the publication date. This is the same estimate-late property Dur-stat Durham showed (Q14).
- The four open items split across two *programs*: two HFI (Environment of Care, Primary Care) and two Information Security — the latter pair are 3+ years old (published 2023-09-27) with null target dates, i.e. long-standing and un-dated. That is a concrete signal the info-security work is the slowest-moving, independent of any prediction.
- `repeat_findings` is empty, and its `_basis` string does the interpretive lifting: "a repeat shows the same issue was cited again, not that nothing was done in between," and comparison happens "only… in a cluster." So the absence of repeats is *not* evidence of no prior issues — it is evidence the templated comparisons found no recurrence across this facility's reports. Easy to misread empty as "clean."
- The two HFI open items are the full output of the *latest* inspection (only 2 recommendations in 25-00193-155), and both are still open — but both target dates precede the next estimated window. That is a checkable, falsifiable statement about which open items are likelier to still be on the board at next inspection, framed explicitly as inference, not a forecast of citations.
- `has_more: true` / `next_offset: 25` on the recommendations list is a reminder that the facility profile paginates recommendations at 25; only 25 of 66 were returned here, so the "4 open" and the repeat-finding comparison depend on the server's own aggregation, not on my reading all 66 rows.

## Q18: When was the VA North Texas Health Care System last inspected by OIG, and when is it next due?

**Tools used:** `vaoig_get_facility_profile` (North Texas → station 549)

**Native Answer:** Last inspected via report 26-00055-01, the HFI of the North Texas system in Dallas, published October 8, 2026 (that report made no recommendations and carries no on-site inspection dates in the record). Next due is an estimate: around October 8, 2029, computed from the publication date plus the ~three-year cycle — OIG doesn't publish a schedule.

**Last inspected: report 26-00055-01, "Healthcare Facility Inspection of the VA North Texas Health Care System in Dallas," published 2026-10-08 (HFI program).** It made **zero recommendations** (`rec_count: 0`), and the record carries **no on-site inspection dates** (`inspection_start`/`inspection_end` are null). The previous inspection was the CHIP report 22-00038-125 (on-site 2022-02-07 to 02-17, published 2023-06-06, two recommendations).

**Next due: 2029-10-08 — an estimate, not a schedule.** `next_window_is_estimate: true`, and it computed from the *publication* date rather than an inspection end date, because the latest report gave no inspection dates and made no recommendations (`next_window_based_on: "published_at"`). OIG publishes no schedule; this is publication + ~3 years.

Source: VA OIG public pages (vaoig.gov). Data as of 2026-11-04.

### OBSERVATIONS
- This is the *fallback branch* of `next_window_basis` firing in the wild — the exact case its text names: "from the publication date where the report gives none, as with an inspection that made no recommendations." North Texas's latest HFI has `rec_count: 0` and null inspection dates, so the estimator anchors on `published_at` (2026-10-08) instead of an on-site end date. Contrast with El Paso (Q17), whose latest HFI had on-site dates and two recommendations and therefore anchored on `inspection_end` (2025-01-16 → 2028-01-16). Same facility-profile tool, two different anchor branches.
- The estimate therefore "tends to run later": the report came out 2026-10-08 but the actual on-site inspection almost certainly happened months earlier in 2026, so the real next cycle is likely *before* the 2029-10-08 figure. The `+3 years from publication` is a conservative outer bound, not a best guess of when OIG will actually return. Worth saying plainly so "2029-10-08" is not read as a scheduled date.
- `open_count: 0` with `recommendation_count: 76` means North Texas is fully closed out — every one of its 76 recommendations is closed. So "next due" here is pure bookkeeping, not a live risk horizon. The facility is not sitting on open findings awaiting re-inspection.
- The latest inspection yielding `rec_count: 0` is itself notable: a "clean" HFI where nothing rose to a recommendation. A reader could misread "0 recommendations" as "0 findings," but the recommendation count is a *threshold* artifact — it records what met the bar for a formal recommendation, not the absence of any observation. `repeat_findings` is also empty (`[]`), consistent with no recurring templated issue, but the empty-`repeat_findings` caveat from Q17 ("not evidence of no prior issues") applies here too.
- "Last inspected" has a real precision limit: the *report* is dated 2026-10-08, but the data does not contain the day the inspectors were physically on site for that HFI. The honest answer is "latest inspection report is dated 2026-10-08, on-site dates not in the record" — not a fabricated on-site window.