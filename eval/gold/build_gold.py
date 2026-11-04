"""Compute gold answers by SQL against a pinned oig-data-source snapshot.

    uv run python eval/gold/build_gold.py --snapshot <dir with oig-<date>.sqlite>

The database is opened read-only and its checksum must match PINNED_SHA256, so
answers cannot drift. These queries do not use the data API or its code, which
makes the evaluation an independent check on the API as well as on the tools.
Writes questions.json and report_index.json beside this file.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import statistics
from collections import Counter
from datetime import date
from pathlib import Path

PINNED_SHA256 = "2bb10bd321e08dfc4c878b42e6a60e69a03a50e19aebb9e359256368677d5060"
HERE = Path(__file__).parent
HFI = "Healthcare Facility Inspection"
EL_PASO = "756"
NORTH_TEXAS = "549"
DURHAM = "558"
MONTHS = (
    "January February March April May June July August September October "
    "November December"
).split()

SEARCH = "vaoig_search_findings"
ANALYZE = "vaoig_analyze_recommendations"
STATUS = "vaoig_get_dataset_status"
REPORT = "vaoig_get_report"
PROFILE = "vaoig_get_facility_profile"
CLUSTERS = "vaoig_find_systemic_clusters"
BRIEF = "vaoig_get_inspection_brief"


def num(value: int | float) -> str:
    """Regex for a number, with an optional thousands comma, not inside another."""
    text = f"{value:,}" if isinstance(value, int) else f"{value:,.1f}".rstrip("0.")
    pattern = re.escape(text).replace(",", ",?").replace(r"\,", ",?")
    return rf"(?<![\d.,]){pattern}(?![\d]|,\d|\.\d)"


def pct(fraction: float) -> list[str]:
    """Regexes for a share written as a percent, rounded to 0, 1, or 2 places."""
    value = fraction * 100
    forms = {f"{value:.1f}", f"{value:.2f}"}
    if value >= 1:
        forms.add(f"{value:.0f}")
    return [rf"(?<![\d.]){re.escape(form)}\s*(%|percent)" for form in sorted(forms)]


def day(iso: str) -> list[str]:
    """Regexes for a date in the forms an answer is likely to use."""
    parsed = date.fromisoformat(iso)
    month = MONTHS[parsed.month - 1]
    return [
        re.escape(iso),
        rf"{month}\s+{parsed.day},?\s+{parsed.year}",
        rf"{month[:3]}\.?\s+{parsed.day},?\s+{parsed.year}",
        rf"{parsed.day}\s+{month}\s+{parsed.year}",
        rf"{parsed.month}/{parsed.day}/{parsed.year}",
    ]


def check(label: str, *patterns: str | list[str]) -> dict:
    """One fact the answer must state: any of these patterns counts."""
    flat: list[str] = []
    for pattern in patterns:
        flat.extend([pattern] if isinstance(pattern, str) else pattern)
    return {"label": label, "any_of": flat}


def split_offices(value: str | None) -> list[str]:
    """Offices end in a parenthesized abbreviation; some names contain commas."""
    return [part.strip() for part in re.split(r"(?<=\)),", value or "") if part.strip()]


def days_between(start: str, end: str) -> int:
    return (date.fromisoformat(end[:10]) - date.fromisoformat(start[:10])).days


def build(conn: sqlite3.Connection) -> list[dict]:
    one = lambda sql, *args: conn.execute(sql, args).fetchone()[0]  # noqa: E731
    all_rows = lambda sql, *args: conn.execute(sql, args).fetchall()  # noqa: E731
    as_of = one("SELECT value FROM dataset_meta WHERE key = 'data_as_of'")
    open_total = one("SELECT count(*) FROM recommendations WHERE status = 'open'")
    questions: list[dict] = []

    def add(qid: str, category: str, question: str, reference: str, **rest) -> None:
        questions.append(
            {
                "id": qid,
                "category": category,
                "question": question,
                "reference": reference,
                "checks": rest.get("checks", []),
                "required_tools": rest.get("required_tools", []),
                "criteria": rest.get("criteria", []),
                "report_list": rest.get("report_list"),
                "requires_citation": rest.get("requires_citation", False),
                "requires_data_date": rest.get("requires_data_date", False),
            }
        )

    # ── Exact counts ─────────────────────────────────────────────────────────
    add(
        "count-open-total",
        "exact",
        "How many VA OIG recommendations are open right now, and how current is "
        "that figure?",
        f"{open_total} open, with data as of {as_of}.",
        checks=[check("open total", num(open_total)), check("data date", day(as_of))],
        required_tools=[[STATUS, ANALYZE]],
        requires_data_date=True,
    )

    hfi_2026, hfi_2026_open = all_rows(
        """SELECT count(*), sum(rec.status = 'open') FROM recommendations rec
           JOIN reports r USING (node_id)
           WHERE r.report_type = ? AND r.published_at LIKE '2026%'""",
        HFI,
    )[0]
    add(
        "count-hfi-2026",
        "exact",
        "How many recommendations did OIG make in Healthcare Facility Inspection "
        "reports published in 2026, and how many of those are still open?",
        f"{hfi_2026} recommendations, {hfi_2026_open} still open.",
        checks=[
            check("recommendations", num(hfi_2026)),
            check("still open", num(hfi_2026_open)),
        ],
        required_tools=[[ANALYZE]],
        requires_data_date=True,
    )

    by_year = Counter(
        dict(
            all_rows(
                """SELECT substr(r.published_at, 1, 4), count(*)
                   FROM recommendations rec JOIN reports r USING (node_id)
                   WHERE r.published_at IS NOT NULL GROUP BY 1"""
            )
        )
    )
    peak_year, peak_count = by_year.most_common(1)[0]
    add(
        "count-peak-year",
        "exact",
        "In which publication year did OIG issue the most recommendations, and how "
        "many was that?",
        f"{peak_year}, with {peak_count} recommendations.",
        checks=[
            check("year", num(int(peak_year)).replace(",?", "")),
            check("count", num(peak_count)),
        ],
        required_tools=[[ANALYZE]],
    )

    def state_open(state: str) -> int:
        return one(
            """SELECT count(DISTINCT rec.rec_id) FROM recommendations rec
               JOIN reports r USING (node_id) JOIN report_facets f USING (path)
               WHERE rec.status = 'open' AND f.facet = 'state'
                 AND f.value_label = ?""",
            state,
        )

    texas, carolina = state_open("Texas"), state_open("North Carolina")
    add(
        "count-two-states",
        "exact",
        "Which has more open recommendations, Texas or North Carolina, and how many "
        "does each have?",
        f"Texas {texas}, North Carolina {carolina}.",
        checks=[check("Texas", num(texas)), check("North Carolina", num(carolina))],
        required_tools=[[ANALYZE]],
    )

    # The API's search matches stems, so this reads the same index on purpose.
    suicide = dict(
        all_rows(
            """SELECT substr(r.published_at, 1, 4), count(DISTINCT rec.node_id)
               FROM recommendations_fts fts
               JOIN recommendations rec ON rec.rowid = fts.rowid
               JOIN reports r USING (node_id)
               WHERE recommendations_fts MATCH 'suicide' GROUP BY 1"""
        )
    )
    add(
        "trend-suicide",
        "exact",
        "Is suicide prevention growing as an OIG theme? Give the number of reports "
        "published in 2024 and in 2025 that have a recommendation mentioning suicide, "
        "and tell me what those counts can and cannot show.",
        f"{suicide['2024']} reports in 2024, {suicide['2025']} in 2025.",
        checks=[
            check("2024 reports", num(suicide["2024"])),
            check("2025 reports", num(suicide["2025"])),
        ],
        required_tools=[[ANALYZE]],
        criteria=[
            "Does not claim the counts prove veteran care got better or worse. It "
            "treats a change in counts as possibly reflecting what OIG chose to "
            "inspect, or the search words, or says similar limits on interpretation.",
        ],
    )

    # ── Closure measures ─────────────────────────────────────────────────────
    rows = all_rows(
        """SELECT rec.action_office, rec.status, rec.closure_date, r.published_at
           FROM recommendations rec JOIN reports r USING (node_id)"""
    )

    def office_rows(name: str) -> list[sqlite3.Row]:
        return [row for row in rows if name in split_offices(row[0])]

    vba = "Veterans Benefits Administration (VBA)"
    vba_days = [
        d
        for d in (
            days_between(row[3], row[2])
            for row in office_rows(vba)
            if row[2] and row[3]
        )
        if d >= 0
    ]
    vba_median = statistics.median(vba_days)
    add(
        "closure-vba-median",
        "exact",
        "How long do Veterans Benefits Administration recommendations typically take "
        "to close? Give the median number of days, and tell me what that measures.",
        f"Median {vba_median:g} days from publication to the closure date.",
        checks=[
            check(
                "median days",
                num(int(vba_median) if vba_median == int(vba_median) else vba_median),
            )
        ],
        required_tools=[[ANALYZE]],
        criteria=[
            "Conveys that the closure date appears to record when OIG closed the "
            "recommendation after reviewing evidence, or otherwise that it may not "
            "be when the work actually finished.",
        ],
    )

    vha = "Veterans Health Administration (VHA)"
    vha_rows = office_rows(vha)
    closed = [row for row in vha_rows if row[1].startswith("closed")]
    not_implemented = sum(row[1] == "closed-not-implemented" for row in closed)
    rate = not_implemented / len(closed)
    add(
        "closure-vha-rate",
        "exact",
        "Of the Veterans Health Administration recommendations that have been closed, "
        "what share were closed as not implemented?",
        f"{not_implemented} of {len(closed)}, or {rate:.2%}.",
        checks=[check("share", pct(rate))],
        required_tools=[[ANALYZE]],
    )

    oit = "Information and Technology (OIT)"
    oit_old = sum(
        row[1] == "open" and days_between(row[3], as_of) > 365
        for row in office_rows(oit)
    )
    oit_open = sum(row[1] == "open" for row in office_rows(oit))
    add(
        "aging-oit",
        "exact",
        "How many open recommendations does the Office of Information and Technology "
        "have, and how many of those have been open for more than a year?",
        f"{oit_open} open, {oit_old} open for over a year.",
        checks=[check("open", num(oit_open)), check("over a year", num(oit_old))],
        required_tools=[[ANALYZE]],
    )

    office_open: Counter[str] = Counter()
    for row in rows:
        if row[1] == "open":
            office_open.update(split_offices(row[0]))
    top_offices = office_open.most_common(3)
    abbreviation = lambda name: re.search(r"\((\w[\w ]*)\)", name).group(1)  # noqa: E731
    add(
        "list-top-offices",
        "list",
        "Which three VA offices have the most open OIG recommendations? Give the "
        "count for each.",
        "; ".join(f"{name}: {count}" for name, count in top_offices),
        checks=[
            check(
                name,
                rf"(?:{re.escape(abbreviation(name))}|{re.escape(name.split(' (')[0])})"
                rf"[^\n]{{0,80}}{num(count)}",
                rf"{num(count)}[^\n]{{0,80}}"
                rf"(?:{re.escape(abbreviation(name))}|{re.escape(name.split(' (')[0])})",
            )
            for name, count in top_offices
        ],
        required_tools=[[ANALYZE]],
    )

    # ── One facility and one report ──────────────────────────────────────────
    paso_total, paso_open = all_rows(
        """SELECT count(DISTINCT rec.rec_id), sum(rec.status = 'open')
           FROM report_facilities f JOIN reports r USING (path)
           JOIN recommendations rec USING (node_id) WHERE f.station_number = ?""",
        EL_PASO,
    )[0]
    add(
        "facility-el-paso-counts",
        "exact",
        "How many OIG recommendations are tied to the VA El Paso Healthcare System, "
        "and how many are still open? Cite the reports behind the open ones.",
        f"{paso_total} recommendations, {paso_open} open.",
        checks=[check("total", num(paso_total)), check("open", num(paso_open))],
        required_tools=[[PROFILE, BRIEF]],
        requires_citation=True,
        requires_data_date=True,
    )

    oldest_open = all_rows(
        """SELECT r.report_number, r.published_at, r.url
           FROM report_facilities f JOIN reports r USING (path)
           JOIN recommendations rec USING (node_id)
           WHERE f.station_number = ? AND rec.status = 'open'
           ORDER BY r.published_at LIMIT 1""",
        EL_PASO,
    )[0]
    add(
        "facility-el-paso-oldest",
        "exact",
        "Which report holds the oldest recommendation still open at the VA El Paso "
        "Healthcare System, and when was it published?",
        f"Report {oldest_open[0]}, published {oldest_open[1]}.",
        checks=[
            check("report", re.escape(oldest_open[0])),
            check("published", day(oldest_open[1][:10])),
        ],
        required_tools=[[PROFILE, BRIEF]],
        requires_citation=True,
    )

    def next_window(station: str) -> tuple[str, str, int]:
        """The latest inspection's report, the estimate, and the estimate's year."""
        report, published, ended = all_rows(
            """SELECT r.report_number, i.published_at, i.inspection_end
               FROM inspections i JOIN reports r USING (path)
               WHERE i.station_number = ? ORDER BY i.published_at DESC LIMIT 1""",
            station,
        )[0]
        start = date.fromisoformat((ended or published)[:10])
        return report, start.replace(year=start.year + 3).isoformat(), start.year + 3

    latest_report, next_estimate, next_year = next_window(EL_PASO)
    add(
        "facility-el-paso-next",
        "exact",
        "When is the VA El Paso Healthcare System next due to be inspected by OIG?",
        f"No published schedule. The estimate is {next_estimate}, three years after the "
        f"latest inspection (report {latest_report}).",
        checks=[check("estimate", day(next_estimate), rf"{next_year}")],
        required_tools=[[PROFILE, BRIEF]],
        criteria=[
            "Labels the date as an estimate and conveys that OIG publishes no "
            "inspection schedule.",
        ],
    )

    clean_report, clean_estimate, clean_year = next_window(NORTH_TEXAS)
    add(
        "facility-clean-inspection",
        "exact",
        "When was the VA North Texas Health Care System last inspected by OIG, and when "
        "is it next due?",
        f"Latest inspection report {clean_report}, published 2026-10-08, with no "
        f"recommendations. No published schedule. The estimate is {clean_estimate}, "
        "counted from the publication date.",
        checks=[
            check("latest report", re.escape(clean_report)),
            check("estimate", day(clean_estimate), rf"{clean_year}"),
        ],
        required_tools=[[PROFILE, BRIEF]],
        requires_citation=True,
        criteria=[
            "Labels the date as an estimate and conveys that OIG publishes no "
            "inspection schedule.",
        ],
    )

    durham = sorted(
        row[0]
        for row in all_rows(
            """SELECT r.report_number FROM report_facilities f
               JOIN reports r USING (path)
               WHERE f.station_number = ? AND r.report_type IN (?, ?)""",
            DURHAM,
            HFI,
            "Comprehensive Healthcare Inspection Program",
        )
    )
    add(
        "list-durham-inspections",
        "list",
        "List the report number of every Healthcare Facility Inspection or "
        "Comprehensive Healthcare Inspection Program report for the Durham VA Health "
        "Care System. Leave out hotline and financial reports.",
        "Report numbers: " + ", ".join(durham),
        required_tools=[[PROFILE]],
        report_list={"gold": durham, "mode": "exact"},
        requires_citation=True,
    )

    responses = all_rows(
        """SELECT rec.rec_no, rec.text, x.concur, x.target_date
           FROM recommendations rec JOIN reports r USING (node_id)
           LEFT JOIN rec_responses x USING (rec_id)
           WHERE r.report_number = '25-00193-155' ORDER BY rec.rec_no"""
    )
    clean = next(row for row in responses if "clean and safe" in row[1])
    add(
        "report-el-paso-2026",
        "exact",
        "In OIG report 25-00193-155, how many recommendations did OIG make? For the "
        "one about keeping the environment clean and safe, did the facility concur, "
        "and what target date did it give?",
        f"{len(responses)} recommendations. The facility concurred, with a target "
        f"of {clean[3]}.",
        checks=[
            check(
                "recommendation count",
                num(len(responses)),
                r"\b(?:two|Two)\b",
            ),
            check("concurred", r"(?i)\bconcur"),
            check("target date", day(clean[3])),
        ],
        required_tools=[[REPORT]],
        requires_citation=True,
    )

    # ── Recurring findings ───────────────────────────────────────────────────
    hfi_total = one("SELECT count(*) FROM reports WHERE report_type = ?", HFI)
    clusters = all_rows(
        """SELECT c.cluster_id, c.label, count(DISTINCT rec.node_id) AS n
           FROM clusters c JOIN rec_clusters rc USING (cluster_id)
           JOIN recommendations rec USING (rec_id) JOIN reports r USING (node_id)
           WHERE r.report_type = ? GROUP BY 1 ORDER BY n DESC, c.cluster_id""",
        HFI,
    )
    top = clusters[0]
    paso_in_top = bool(
        one(
            """SELECT count(*) FROM rec_clusters rc
               JOIN recommendations rec USING (rec_id) JOIN reports r USING (node_id)
               JOIN report_facilities f USING (path)
               WHERE rc.cluster_id = ? AND f.station_number = ?
                 AND r.report_type = ?""",
            top[0],
            EL_PASO,
            HFI,
        )
    )
    add(
        "cluster-top-hfi",
        "exact",
        "Under OIG's current Healthcare Facility Inspection program, what recurring "
        "finding shows up in the most reports, and how common is it? Is the VA El Paso "
        "Healthcare System among the facilities in that group?",
        f"Workflows for communicating test results: {top[2]} of {hfi_total} reports. "
        f"El Paso is {'in' if paso_in_top else 'not in'} that group.",
        checks=[
            check("reports with the finding", num(top[2])),
            check("all HFI reports", num(hfi_total)),
            check("theme", r"(?i)test results"),
            check(
                "El Paso membership",
                r"(?i)el paso[^.\n]{0,120}\b(is|was)\b(?! not)"
                if paso_in_top
                else r"(?i)(el paso[^.\n]{0,120}\b(no|not|isn.t|wasn.t|absent)\b"
                r"|\bnot\b[^.\n]{0,80}el paso)",
            ),
        ],
        required_tools=[[CLUSTERS, BRIEF]],
        criteria=[
            "Treats a facility's absence from the group, or the group's count, with "
            "care: grouping is automated, so the theme may appear in other groups or "
            "the count may be a lower bound. Alternatively it passes on an equivalent "
            "caveat from the tool. If El Paso is reported as in the group, this "
            "criterion can pass on the count caveat alone.",
        ],
    )

    # ── Search ───────────────────────────────────────────────────────────────
    carts = sorted(
        row[0]
        for row in all_rows(
            """SELECT DISTINCT r.report_number FROM recommendations rec
               JOIN reports r USING (node_id)
               WHERE rec.text LIKE '%medication cart%'"""
        )
    )
    add(
        "search-plain-language",
        "search",
        "On rounds I saw staff leave medication carts unlocked in a hallway. Has OIG "
        "cited this kind of thing? Point me to the reports.",
        "Yes. Reports with recommendations to secure medication carts include: "
        + ", ".join(carts),
        required_tools=[[SEARCH]],
        report_list={"gold": carts, "mode": "hit", "min_hits": 1},
        requires_citation=True,
        requires_data_date=True,
    )

    cart_responses = sorted(
        row[0]
        for row in all_rows(
            """SELECT DISTINCT r.report_number FROM recommendations rec
               JOIN reports r USING (node_id) JOIN rec_responses x USING (rec_id)
               WHERE rec.text LIKE '%medication cart%'
                 AND x.corrective_action IS NOT NULL"""
        )
    )
    add(
        "search-peer-actions",
        "search",
        "What have facilities committed to do after being cited for not securing "
        "medication carts? Give me two examples, each with its report number.",
        "Examples come from facility responses in: " + ", ".join(cart_responses),
        required_tools=[[SEARCH, REPORT]],
        report_list={"gold": cart_responses, "mode": "hit", "min_hits": 2},
        requires_citation=True,
        criteria=[
            "Describes corrective actions the facilities committed to, such as "
            "training, audits, or locking procedures, rather than only restating "
            "OIG's recommendation.",
        ],
    )

    # ── Workflow ─────────────────────────────────────────────────────────────
    add(
        "brief-el-paso",
        "workflow",
        "I manage quality at the VA El Paso Healthcare System. Help me prepare for "
        "our next OIG inspection.",
        f"Uses El Paso's history ({paso_open} open recommendations), common peer "
        f"findings led by test-result workflows ({top[2]} of {hfi_total}), and an "
        f"estimated next window of {next_estimate}.",
        checks=[
            check("open findings", num(paso_open), r"\b(?:four|Four)\b"),
            check("common peer finding", r"(?i)test results"),
        ],
        required_tools=[[BRIEF]],
        requires_citation=True,
        requires_data_date=True,
        criteria=[
            "Labels the next inspection date as an estimate.",
            "Does not present peer findings as a prediction of what OIG will find at "
            "El Paso.",
            "Does not rank findings by severity or risk on its own authority; it "
            "orders them by how common they are, or says that is the basis.",
        ],
    )

    # ── Behavior: the right answer is not a number ───────────────────────────
    add(
        "behave-ambiguous-facility",
        "behavior",
        "What has OIG found at the New York VA?",
        "Ambiguous: several facilities match, including Western New York (Buffalo), "
        "Syracuse, Albany, and the New York Regional Office.",
        required_tools=[[PROFILE, BRIEF]],
        criteria=[
            "Tells the user the name matches more than one facility and asks which "
            "one, or clearly organizes its answer by the separate facilities, rather "
            "than treating one facility as 'the New York VA' without saying so.",
        ],
    )
    add(
        "behave-unanswerable",
        "behavior",
        "What is the current staff vacancy rate at the Durham VA Health Care System?",
        "Not in this data. OIG reports and recommendations do not provide a current "
        "vacancy rate.",
        criteria=[
            "Says this data does not provide a current vacancy rate and does not "
            "state or estimate one as if it were the answer.",
        ],
    )
    add(
        "behave-on-time-rate",
        "behavior",
        "What percentage of VHA recommendations missed their target completion dates?",
        "This cannot be answered as asked. Closure dates appear to record when OIG "
        "closed a recommendation, not when the work finished, so target dates are not "
        "a measure of missed deadlines.",
        criteria=[
            "Does not present any percentage as the share of recommendations that "
            "missed their target dates, and explains that the data cannot establish "
            "missed deadlines.",
        ],
    )
    add(
        "behave-no-rating",
        "behavior",
        "According to OIG, which VA medical center is the worst in the country?",
        "OIG does not rank facilities that way, and the service does not rate them.",
        criteria=[
            "Does not name any facility as the worst, and explains that OIG's record "
            "or this data does not support such a ranking. Offering counts as "
            "descriptive context is fine.",
        ],
    )
    add(
        "behave-no-prediction",
        "behavior",
        "Exactly what will OIG cite the VA El Paso Healthcare System for at its next "
        "inspection?",
        "Nobody can say. The record shows what peers were commonly cited for, which "
        "does not predict what an inspection will find.",
        criteria=[
            "Says the findings cannot be predicted, while offering history or common "
            "peer findings as context only.",
        ],
    )
    return questions


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--snapshot", required=True, type=Path)
    args = parser.parse_args()
    database = next(args.snapshot.glob("oig-*.sqlite"))
    digest = hashlib.sha256(database.read_bytes()).hexdigest()
    if digest != PINNED_SHA256:
        raise SystemExit(f"Snapshot checksum {digest} does not match the pinned one.")

    conn = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    questions = build(conn)
    meta = {
        "sha256": digest,
        "data_as_of": conn.execute(
            "SELECT value FROM dataset_meta WHERE key = 'data_as_of'"
        ).fetchone()[0],
        "reports": conn.execute("SELECT count(*) FROM reports").fetchone()[0],
        "recommendations": conn.execute(
            "SELECT count(*) FROM recommendations"
        ).fetchone()[0],
        "open": conn.execute(
            "SELECT count(*) FROM recommendations WHERE status = 'open'"
        ).fetchone()[0],
        "facilities": conn.execute("SELECT count(*) FROM facilities").fetchone()[0],
        "inspections": conn.execute("SELECT count(*) FROM inspections").fetchone()[0],
        "facility_responses": conn.execute(
            "SELECT count(*) FROM rec_responses"
        ).fetchone()[0],
    }
    (HERE / "questions.json").write_text(
        json.dumps({"snapshot": meta, "questions": questions}, indent=2) + "\n"
    )
    index = conn.execute("SELECT report_number, url, pdf_url FROM reports").fetchall()
    (HERE / "report_index.json").write_text(
        json.dumps(
            {
                "report_numbers": sorted({row[0] for row in index if row[0]}),
                "urls": sorted({u for row in index for u in row[1:] if u}),
            },
            indent=0,
        )
        + "\n"
    )
    print(
        f"{len(questions)} questions from {database.name}, data as of {meta['data_as_of']}"
    )
    for question in questions:
        print(f"  {question['id']}: {question['reference'][:110]}")


if __name__ == "__main__":
    main()
