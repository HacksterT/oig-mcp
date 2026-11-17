# The data pipeline behind the server

*How VA OIG's public website becomes the data this server answers from. The pipeline lives in a separate, private repository, `oig-data-source`; this page describes what it does so its work can be judged without it. Figures are from the full build of November 4, 2026, read from the data API's `meta` endpoint. The API contract the server relies on is in [data-api.md](data-api.md).*

OIG publishes every report and recommendation, and its website is good at finding one document. It has no API or bulk export, and the facts that matter across reports, such as what facilities committed to do, sit inside about 2,200 PDFs. The pipeline turns that public record into one structured, checked, searchable dataset, so that each of this server's tools is a query rather than an afternoon of reading.

```
vaoig.gov → crawl → parse → extract responses → link facilities → cluster → index → check → publish → read-only API → this server
```

## Stages

| Stage | What it does | Output (November 4 build) | How it was checked |
|---|---|---|---|
| Crawl | Reads OIG's listing pages, report pages, and PDFs, one request at a time and at least 1.5 seconds apart, identifying itself, backing off when asked. Everything fetched is kept unchanged, so parsing can be fixed and rerun without contacting OIG again. | About 6,100 fetches over nearly three hours; 4,415 report listings, 2,214 PDFs | Crawl rules enforced in one client by construction, with tests |
| Parse | Turns report and recommendation pages into records: status, responsible office, closure date, report type, topic, state, and VISN tags. Text is extracted from PDFs page by page. | 4,410 reports (OIG lists five twice), 15,649 recommendations, 89,188 PDF pages | Every PDF had a usable text layer, so no OCR was needed. A change of PDF extractor removed split words ("r andom") from 13,392 to 60 and page footers in corrective actions from 1,813 to 1 |
| Extract facility responses | Rule-based parsers, not an LLM, read each inspection report's response section: whether the facility concurred, its target date, and its corrective action. Each block is anchored on the target-date line, the most consistent marker in the corpus. | 11,264 facility responses: all 90 Healthcare Facility Inspection reports, and 96 percent of the 312 Comprehensive Healthcare Inspection Program reports from 2018 on | Each response checked against OIG's own text for the recommendation it belongs to; when the extractor changed, every parsed response was compared with the previous build |
| Link facilities | Ties each report to a VA facility by the station number in its memo header, or by the facility name in its title, and records which. A short reviewed list corrects memos that give a parent station or a wrong number, without rewriting OIG's text. | 159 facilities; 2,332 report links (1,311 by station number, 1,021 by title); 1,232 inspections | Duplicate listings and names shared by two stations are reported on every build |
| Cluster | Groups recommendations that recur across reports, by two methods, because older reports reuse templated wording and current inspections do not: matching the first 12 normalized words across 5 or more reports, and, for current inspections, meaning (cosine similarity of at least 0.88 to one central recommendation) across 3 or more reports. | 283 clusters: 259 by wording, 24 by meaning | The weakest members of each meaning-based cluster were reviewed: most fit, and a few are off theme, which the server's cluster results say |
| Index for search | Builds keyword indexes (BM25) and, with an embedding model that runs locally, meaning vectors for every recommendation and corrective action. A search runs both and merges them by reciprocal rank fusion. | Every recommendation and corrective action has a vector | Gates require vectors for at least 99 percent (both were 100) |
| Check, then publish | Compares the build with what OIG publishes and runs six data gates that catch silent loss, such as a page change that empties a field. A build that fails a gate is not published. | Passed: no failed gates | See below |
| Serve | A read-only API over the published database, with every query written ahead of time and every value bound: neither the server nor a model writes SQL. Reachable only through Cloudflare Access with a service token and its own API key. | The endpoints in [data-api.md](data-api.md) | Its own test suite, and this server's deployment checks of its credentials |

## Checks that keep a bad build from being served

**Reconciliation with OIG.** OIG prints 586 open recommendations and 15,778 in total; the build has 567 and 15,649. Totals alone would suggest missing data, so every build compares OIG's listing row by row. On November 4 the same recommendation IDs were in both, none missing either way, and all 14,223 closure dates agreed. The differences are blank rows on OIG's own pages, and the server says so when it reports the open total.

**Data gates.**

| Gate | November 4 | Threshold |
|---|---|---|
| Closed recommendations with a closure date | 94.3% | 90% |
| Reports with recommendations having a PDF | 99.3% | 90% |
| Reports with recommendations having a summary | 99.9% | 80% |
| Recommendations with a vector | 100% | 99% |
| Corrective actions with a vector | 100% | 99% |
| Reports with a state or VISN | 74.3% | 25% |

**Quality checks** report without failing a build: orphan rows, impossible dates, recommendations missing from the latest listing, office labels not on OIG's list, names shared by two stations, and inspection reports with no facility.

**A pinned snapshot.** Each build is written to a dated snapshot with checksums. The evaluation pins one by checksum, and the harness stops if the server's data differs, because the gold answers would no longer apply.

## Design choices

- **Finding and counting are separate.** Search is a ranked shortlist with no natural end, so nothing is counted from it. Every count is an exact database query, and the same question always returns the same number.
- **No AI in the data path.** Extraction is rule-based and deterministic, and embeddings run locally, so no report text or query leaves the machine for processing. The tradeoff is lower coverage on report types without a consistent response format.
- **OIG's text is never rewritten.** Corrections, such as a mistyped station number, are applied as a reviewed list when derived tables are built.

## What search adds, and what it does not

Search blends keywords and meaning, so a plain sentence such as "staff left medication carts unlocked in a hallway" finds recommendations worded "secure medication carts when not in use." That is a gain in reach and access, not in precision. In a ten-question comparison judged by AI, a full sentence here found something relevant on 8 of 10 questions, against 0 of 10 for the same sentence on OIG's search. On identical short keywords, OIG's results were more often relevant: 50 percent against 34. No search found anything relevant on two of the ten questions. The judgments were made by AI, not by people, and the questions were written by the builder, so the figures are directional.

## Known limits

- **PDF coverage.** PDFs are collected for reports with recommendations. The 2,186 reports without recommendations are listed and searchable by title, but their text is not included. Facility responses are extracted mainly from inspection reports, so a finding without one does not mean the facility did not respond.
- **Closure dates.** A closure date appears to record when OIG closed a recommendation after reviewing evidence, not when the work was finished, and about 6 percent of closed recommendations, mostly from 2013 to 2016, show none on OIG's site. Time to close describes OIG's process as much as the facility's, and target dates are never treated as missed deadlines.
- **Topics.** OIG tagged only about a quarter of reports with a topic, so topic counts cover only those.
- **VISN realignment.** VA replaced its 18 VISNs with five on July 15, 2026. OIG labels reports from August 2026 with the new networks and did not retag older ones, so labels 1, 2, 4, and 5 each name two different regions. The data keeps OIG's labels; the server warns whenever a VISN filter is used and suggests filtering by state.
- **Clusters are automated.** A facility missing from a cluster may still have been cited for that theme in other words, and a repeat finding means an issue was cited again, not that nothing was done in between.
- **One machine.** The API runs on a single local machine; a dated snapshot allows it to move to a cloud host without changing this server.
