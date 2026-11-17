[Wiki](../README.md) › Guides › Tools

# Tools

*The seven tools: what each is for, when to use another instead, and its main inputs. Each tool's full description and schemas are what a host receives from `tools/list`.*

Every tool is read-only. Every data result carries `provenance` and `notices`, and records carry a ready-made `citation` ([MCP features](../architecture/mcp-features.md#provenance-notices-and-citations)).

## Choosing a tool

| The question | Tool |
|---|---|
| How current is the data? What values can a filter take? | `vaoig_get_dataset_status` |
| Find findings, or what peer facilities committed to do | `vaoig_search_findings` |
| How many, a trend over time, time to close, how old open items are | `vaoig_analyze_recommendations` |
| What recurs across facilities, and how common it is | `vaoig_find_systemic_clusters` |
| One report in full | `vaoig_get_report` |
| One facility's record | `vaoig_get_facility_profile` |
| Preparing one facility for an inspection | `vaoig_get_inspection_brief` |

## vaoig_get_dataset_status

How current the data is, what it covers, and the valid filter values. Call it first when an answer depends on current status, or to look up an exact status, office, topic, or report type. No inputs.

## vaoig_search_findings

Finds recommendations and corrective actions matching a question in any wording, including a full sentence, by keywords and meaning together. Results are a ranked shortlist, never a count: use the analysis tool to count. For one named facility, use the facility tools, because a search on a facility's name finds only text that mentions it.

| Input | Meaning |
|---|---|
| `question` | What to find, in any wording |
| `filters` | Status, office, topic, report type, state, dates, and `exclude_station_number` to leave out the asking facility |
| `limit`, `offset` | Paging, up to 100 a page |

## vaoig_analyze_recommendations

Exact counts and measures over a filtered set: trends by year, time to close, not-implemented rates, and the age of open items, grouped by year, office, topic, or report type. It does not rate facilities, so facility is not a grouping, and it does not compute whether target dates were met, because the data cannot establish that. A state-filtered result names the facilities it pools.

| Input | Meaning |
|---|---|
| `group_by` | `year`, `office`, `topic`, or `report_type` |
| `keywords` | Limit to recommendations containing all of these words |
| `filters` | As for search |

## vaoig_find_systemic_clusters

Findings that recur across reports: how common each is, as report prevalence, and how long similar findings take to close. Set `report_type` for one program, such as the current Healthcare Facility Inspection program; open one cluster with `cluster_id` to see its members and check whether a facility is among them.

| Input | Meaning |
|---|---|
| `cluster_id` | Open one cluster with its members |
| `wording`, `min_reports`, `active_since`, `report_type`, `domain`, `published_from` | Narrow the clusters |
| `limit`, `offset` | Paging |

## vaoig_get_report

One report with every recommendation, its status, closure date, status history, and the facility's response, plus the summary, PDF link, monetary impact, and standards cited. Provide `report_number` (such as `15-00071-158`) or `node_id` from another tool's result.

## vaoig_get_facility_profile

One facility's reports, inspections, findings with their status, and repeat findings, with counts of recommendations and open items. Accepts a facility name, city, or station number. A name that matches several facilities returns the matches and a next step to ask the user, or, in a host that supports it, asks the user directly ([Elicitation](../architecture/mcp-features.md#elicitation)).

| Input | Meaning |
|---|---|
| `facility` | Name, city, or station number |
| `limit`, `offset` | Paging through recommendations, newest 100 first |

## vaoig_get_inspection_brief

Prepares one facility for an inspection from the public record: its open findings with its responses, its repeat findings, the most common findings among its peers with how common each is and whether this facility is among them, what peers committed to do, typical time to close, and an estimated next inspection window, labeled as the server's estimate because OIG publishes no schedule.

| Input | Meaning |
|---|---|
| `facility` | Name, city, or station number |
| `top_findings` | Common peer findings to include, 1 to 10 |

## Resources and prompts

`vaoig://about`, `vaoig://facilities`, and `vaoig://taxonomy/{facet}` give scope, the facility registry, and filter values. The prompts `inspection_readiness_checklist` and `open_recommendation_aging_brief` package two common workflows.

---

← [Connecting](../guides/connecting.md) · [Wiki home](../README.md) · [Deployment and operations](../guides/deployment.md) →
