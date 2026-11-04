# OIG Data API contract

This server reads all of its data from one HTTP API, built and hosted by the `oig-data-source` repository (a Python API over a SQLite database, run in a container on Troy's Mac and exposed through Cloudflare Tunnel with Access service tokens). This file records what the MCP server expects from that API. The endpoints below are implemented in `oig-data-source`, not here.

The API is deliberately generic: filter, paginate, and aggregate over reports, recommendations, facilities, clusters, and facility responses. The MCP tools compose these calls into goal-level answers. An endpoint that mirrors one tool is a sign that logic has leaked from the server into the API.

## Conventions

- Base URL: `OIG_DATA_API_BASE_URL`, for example `http://127.0.0.1:8787/v1/` with the oig-data-source container running (`docker compose up -d`).
- Auth: `CF-Access-Client-Id` and `CF-Access-Client-Secret` headers when hosted; none locally.
- All responses are JSON. Lists use the envelope `{total, count, offset, items, has_more, next_offset}`.
- Every response includes `data_as_of` (YYYY-MM-DD).
- Reports are keyed by `node_id` (the vaoig.gov Drupal node id); recommendations by `rec_id` = `<node_id>-<rec_no>`. vaoig.gov exposes a node id only for reports that have recommendations (about half of all reports; oig-data-source ADR-04), so report list items also carry `path`, and `node_id` may be null there.
- Status values: `open`, `closed-implemented`, `closed-not-implemented`.

## Endpoints

| Method and path | Returns | Used by |
|---|---|---|
| `GET meta` | `data_as_of`, `counts`, `reconciliation` (database open counts versus the OIG dashboard), migration and parser versions | `vaoig_get_dataset_status` (implemented) |
| `GET search` | **The one search call.** A question in any wording; keyword and semantic results fused into one ranked list, plus PDF page hits | search findings, peer corrective actions |
| `GET recommendations` | Recommendations filtered by `q` (FTS5), `status`, `action_office`, `topic`, `report_type`, `visn`, `state`, `published_from`, `published_to`; paginated | search, trends, facility profile |
| `GET reports` | Reports filtered by `q` (title), `report_type`, `topic`, `visn`, `state`, dates, `report_number`, `path`, `has_recommendations`; paginated; reaches reports with no node id | report lookup |
| `GET reports/{node_id}` | One report with all recommendations, closure dates, facility responses, standards cited, PDF URL | report detail |
| `GET pages/search` | PDF page hits for `q` with `node_id`, `page_no`, snippet | narrative search |
| `GET facilities` and `GET facilities/{station_number}` | Facility registry; one facility's reports, inspections, and recommendations | facility profile, inspection readiness |
| `GET inspections` | Inspections by facility, program, and date, with the next-window estimate | inspection readiness |
| `GET clusters` and `GET clusters/{cluster_id}` | Templated recommendation clusters with member reports and statuses | systemic clusters |
| `GET metrics/closure` | Median and interquartile days to closure and not-implemented rate, grouped by `office`, `topic`, or `report_type` | closure performance |
| `GET metrics/counts` | Report and recommendation counts by year for a filter set | theme trend |
| `GET taxonomy/{facet}` | OIG facet values (topics, offices, states, VISNs) | resources |

## One search tool

Expose one search tool to the assistant, backed by `GET search`, with no mode or strategy parameter. Several similar search tools make an assistant guess between them, and the pipeline already runs every method on every query. `GET recommendations`, `pages/search`, and the metrics endpoints are for exact listing and counting inside other tools, not for separate search tools.

Use `GET search` to find; use `GET recommendations` and `metrics/*` to count. A search result is a ranked shortlist with no natural end, so its `total` is never a count of findings.

## Tool surface

Two decisions from Troy (2026-11-04) keep the tool list short:

- **One analysis tool.** Merge the planned `vaoig_get_theme_trend` and `vaoig_get_closure_performance` into one tool that filters a set and groups it by year, office, topic, or report type. Both are the same shape, and two of them would make an assistant guess. It calls `metrics/counts` and `metrics/closure`.
- **New facts belong in existing tools.** Repeat findings, how common a finding is, how long it takes to close, and promised versus actual dates are fields below, not new tools.

Lead with what OIG's site cannot do: facilities' committed corrective actions, cross-report recurrence, trends, and time to close. OIG already offers solid keyword search and filters, so do not compete there.

## Implemented

Every endpoint above is live as of 2026-11-04. The API's own OpenAPI document is at `/openapi.json` and interactive docs at `/docs`.

**Shared parameters.** `limit` (1 to 100, default 20) and `offset` (0 or more). An invalid value returns 422 with the parameter named in `detail[].loc`. `q` is full-text search (SQLite FTS5, porter stemming, BM25 ranking). With the default `q_mode=terms`, each word is quoted and all must match, so stray quotes or operators in user text are harmless, but a whole sentence usually finds nothing. `q_mode=any` matches any meaningful word. `q_mode=raw` passes FTS5 syntax through (`OR`, `NEAR`, phrases, prefix `*`). A raw query with bad syntax returns 400. Report filters are `report_type` (slug or label, for example `audit` or `Healthcare Facility Inspection`), `topic`, `visn`, `state` (label, case-insensitive, or the site's term id), `published_from` and `published_to` (YYYY-MM-DD, inclusive), `report_number`, `station_number`, and `exclude_station_number` (to see only a facility's peers).

**`GET search`.** Requires `q`, in any wording, including a whole sentence. Takes the `recommendations` filters, `limit`, and `offset`. Every query runs keyword (BM25) and semantic (`nomic-embed-text`) search over recommendations and over corrective actions, merged by reciprocal rank fusion. Items are the `recommendations` items plus `matched_by`, the lists that found the item (`keyword:recommendation`, `semantic:recommendation`, `keyword:corrective_action`, `semantic:corrective_action`). `total` is the shortlist size, at most 100. `page_hits` holds up to 5 PDF pages on the first page of results, with `node_id`, `page_no`, `snippet`, `report_number`, `title`, `url`, `pdf_url`, and `published_at`. `search_mode` is `hybrid`, or `keyword_fallback` when the embedding model is unavailable; results are still valid, but report the fallback rather than hiding it.

**`GET /health/search`** (outside `/v1/`). `status` is `ok` or `degraded`, with `model_reachable`, `vectors` (count by kind), `searches_since_start`, and `keyword_fallbacks_since_start`. `/health` only says the process is up.

**`GET meta`.** `counts` adds `facility_responses`, `facilities`, `inspections`, and `clusters`. `reconciliation` compares the database with the totals OIG prints on `/recommendations-all` on `checked_on`: for each of `open`, `total_recommendations`, and `total_reports`, the `database` and `oig` values, the `difference`, and `within_tolerance`, plus `oig_open_by_age`. `derived` records how the derived tables were built, including the cluster method.

**`GET recommendations`.** The exact, countable listing. Adds `status` (repeat the parameter for several values), `action_office`, `node_id`, `domain`, `has_response`, `past_target` (open, with the facility's target date already passed), and `sort` (`relevance`, `newest`, `oldest`). `sort` defaults to `relevance` when `q` is set and `newest` otherwise. An `action_office` abbreviation such as `VHA` or `EHRM IO` matches the parenthesized form; any other value matches part of the office name. One recommendation can name several offices, joined by commas in `action_office`. Each item has `rec_id`, `node_id`, `rec_no`, `text`, `action_office`, `status`, `closure_date`, `report_number`, `title`, `published_at`, `url`, `report_type`, and `response` (the same object as in report detail, or null).

**`GET reports`.** Adds `path` and `has_recommendations`. Each item has `node_id` (nullable), `path`, `report_number`, `title`, `url`, `report_type`, `published_at`, `rec_count`, `open_count`, and `topics`.

**`GET reports/{node_id}`.** Returns the report fields plus `summary`, `pdf_url`, `monetary_impact` (`open` and `closed`, in dollars, as OIG totals them on the listing), `questioned_costs` and `better_use_of_funds` (from the report page), `facets` (facet name to labels), `standards_cited`, and `recommendations`. Each recommendation adds `response` (`domain`, `concur`, `target_date`, `target_date_precision`, `target_date_raw`, `corrective_action`, `page_no`, or null) and `status_history` (one `{observed_at, status, closure_date}` per crawl). `target_date` is `YYYY-MM-DD` at `day` precision and `YYYY-MM` at `month` precision; `target_date_raw` is the wording in the report, including values such as "Completed" that have no date. An unknown node id returns 404.

**`GET pages/search`.** Requires `q`; takes `q_mode`, `node_id`, and the report filters. Items have `node_id`, `page_no` (the physical PDF page), `snippet` (matches wrapped in `**`), `report_number`, `title`, `url`, `pdf_url`, `published_at`, and `report_type`, in BM25 order. Only reports with recommendations have PDF text; the other reports on the site are not indexed.

**`GET facilities`.** Filters are `q` (part of a name, an alias, or a linked report's title, which is how a city such as "West Haven" finds its system; or an exact station number), `visn` (number, for example `17`), and `state`. Items have `station_number`, `name`, `aliases`, `visn`, `state`, `report_count`, `recommendation_count`, and `open_count`. The registry holds facilities named by a station number in a report's memo headers.

**`GET facilities/{station_number}`.** The same fields plus `reports` (each with `link_method`: `station_number` when the PDF says so, `title_match` when inferred from the title), `inspections`, `next_window_basis`, and `recommendations`, which carry report fields and the flat response fields `domain`, `concur`, `target_date`, `target_date_precision`, `corrective_action`, and `response_page_no`. `repeat_findings` lists clusters the facility was cited under in two or more of its reports (`cluster_id`, `label`, `report_count`, `first_published`, `last_published`, `status_counts`, `rec_ids`), and `repeat_findings_basis` states what that does and does not show; pass it on, since a repeat means the same issue was cited again and not that nothing was done. Each recommendation also has `cluster_id`. An unknown station returns 404.

**`GET inspections`.** Filters are `station_number`, `program` (`HFI`, `CHIP`, or `CAP`, the program before CHIP), `published_from`, `published_to`, and `latest_only`. Items have `node_id`, `station_number`, `facility_name`, `program`, `inspection_start`, `inspection_end`, `published_at`, `report_number`, `title`, `url`, `is_latest`, `next_window_estimate`, and `next_window_is_estimate`. The estimate is set only on a facility's latest inspection and is the inspection end (or publication date) plus three years. **It is an estimate and must be labeled as one wherever it is shown**; `next_window_basis` in the response states why. OIG publishes no schedule.

**`GET clusters`.** Filters are `q` (wording in the label or any member), `min_reports`, `active_since` (a year), and the member filters `report_type`, `domain`, and `published_from`. Items have `cluster_id`, `label` (one member's text), `method`, `threshold`, `member_count`, `report_count`, `matching_report_count` (reports passing the member filters, which is what `min_reports` tests), `first_year`, `last_year`, `open_count`, and a closure benchmark following the same filters (`days_sample_size`, `median_days`, `q1_days`, `q3_days`, `not_implemented_rate`), ordered by `matching_report_count`. The response adds `reports_in_scope`, every report matching `report_type` and `published_from`, including those with no recommendations. `matching_report_count` over `reports_in_scope` says how common a finding is; report that rather than a bare count. Use `report_type=healthcare-facility-inspection` for findings under the current program. A cluster is a group of recommendations whose opening words match after the addressee, numbers, punctuation, and facility names are removed, across five or more reports. It suggests a shared template; it does not prove a common cause.

**`GET clusters/{cluster_id}`.** The same fields, with the benchmark over all members, plus `status_counts` and `members`, the recommendations with status, closure date, report fields, `station_number`, and `facility_name`. An unknown cluster returns 404.

**`GET metrics/closure`.** Requires `group_by` (`office`, `topic`, or `report_type`) and takes every `recommendations` filter and `q`. Items have `group`, `group_size`, `open_count`, `closed_count`, `closed_implemented_count`, `closed_not_implemented_count`, `not_implemented_rate` (share of closed), `days_sample_size`, `excluded_negative_days`, `median_days`, `q1_days`, `q3_days`, `open_median_age_days`, `open_oldest_age_days`, `open_over_1_year_count`, and, for promised versus actual, `with_target_date`, `closed_by_target`, `closed_after_target`, `closed_by_target_rate`, `median_days_after_target`, and `open_past_target`. Those count only recommendations with a parsed target date, so read them with `with_target_date`; a month-precision target runs to month end. There is deliberately no `group_by=facility`: the server does not rate facilities. Days run from publication to closure, and a closure dated before publication is left out of the day statistics and counted in `excluded_negative_days`. A recommendation naming two offices counts for both, and a report with two topics counts for both, so group sizes can sum to more than the filtered total. Two gaps in OIG's own data should be stated when they matter: OIG tagged only about a quarter of reports with a topic, so `group_by=topic` and the `topic` filter cover only those; and about 6 percent of closed recommendations, mostly from 2013 to 2016, show no closure date on OIG's site, which is why `days_sample_size` can be smaller than `closed_count`.

**`GET metrics/counts`.** Takes the same filters. Items are years, with `year`, `report_count`, `recommendation_count`, `open_count`, `closed_implemented_count`, `closed_not_implemented_count`, and `median_days_to_closure`. `report_count` counts every matching report when only report filters are set, including reports with no recommendations; with `q`, `status`, `action_office`, or `node_id` it counts reports with a matching recommendation.

**`GET taxonomy/{facet}`.** Facets are `topic`, `state`, `visn`, `district`, `mmc`, `author_office`, `special_project`, `action_office`, and `report_type`. The response uses the list envelope plus `facet`, with every value on one page. Items have `value` and `report_count`. Report facets add `value_id`. `action_office` adds `abbreviation`, `recommendation_count`, and `open_count`. `report_type` adds `label`. An unknown facet returns 404.
