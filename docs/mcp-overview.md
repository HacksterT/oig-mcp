# VA OIG Recommendations Assistant: Overview

*For leaders and staff. Status and figures as of November 4, 2026, using data collected October 28, 2026.*

## In brief

The VA Office of Inspector General (OIG) has published thousands of reports. Its website is good at finding a document. It is not built to answer a question that spans many documents, such as "what keeps being cited?" or "what did other facilities commit to do about it?" Today, answering those questions means hours of reading reports and PDFs.

This project connects an AI assistant to a structured copy of what OIG publishes, currently 4,413 reports and 15,647 recommendations. Staff ask a question in plain language and get an answer drawn from across all of them, with a report number and link for every finding. The connector is called an MCP server, which is simply a standard way for an AI assistant to use an outside data source.

It uses only public information from vaoig.gov and no internal VA systems. It is not an official VA or OIG product, and it does not replace VA's own tracking of recommendations.

## Where it goes beyond OIG's website

OIG's search is solid, and this project does not try to replace it. If you know what you are looking for, the site's keywords and filters will find it, and every answer here links back to the site. The difference is in what happens after the search.

| What you need | On OIG's website | With this assistant |
|---|---|---|
| Find a report or recommendation | Keywords plus filters for date, report type, topic, office, status, and location | Ask in your own words. It looks for matching meaning as well as matching words |
| See how an issue changes over time | One total per search, so you repeat the search for each year and tally the results | A year-by-year table from one question |
| See how old open items are | Site-wide totals in three age bands, and a filter for each band | Typical and oldest age, compared across offices, topics, or report types |
| Learn how long fixes take | A closure date on each closed recommendation, with no averages | Typical time to close, the usual range, and the share not implemented\* |
| See what facilities committed to do | Only in the report PDFs | Searchable commitments and target dates across reports\* |
| Spot what recurs across facilities | Read the reports and compare them yourself | Near-identical findings grouped, showing how many reports contain them\* |
| Compare promises with results | Not available | Target dates compared with actual closure dates\* |

\*Available when the current data build finishes. See "Where it stands today."

## For leaders

The value is turning a published archive into something an organization can learn from. A program office can see whether a finding is isolated or systemic before deciding on a national fix. A facility can learn from how its peers responded rather than starting from nothing. Oversight staff can see what is aging and where.

The design favors trust over polish:

- **Every finding can be checked.** It carries a report number, a link to vaoig.gov, and the date the data was collected.
- **It does not rate anyone.** It reports records and offers no facility scores or rankings. Grouping results by facility is deliberately not offered.
- **It states its limits in the answer.** A repeat finding means the same issue was cited again, not that nothing was done. A next-inspection date is labeled as an estimate, because OIG publishes no schedule. Where a pattern has more than one explanation, it gives both.

## For staff

You would use this through an AI assistant, with no new search screens to learn. Ask the way you would ask a colleague:

- "What have facilities been cited for on securing medications, and which of those are still open?"
- "How many suicide prevention findings has OIG made each year since 2020?"
- "Which offices have the most recommendations open longer than a year?"
- "Show me everything in report 24-03416-237."

Use the links to confirm anything you plan to act on or repeat. OIG's site remains the official record.

## Use case 1: "Has OIG cited this?"

**The situation.** A patient safety manager notices a problem on rounds and describes it in plain language: "Staff left medication carts unlocked in a hallway."

**Why this is hard today.** OIG's wording is different. Its reports say things like "secure medication carts when not in use," which shares few words with how the manager put it. A word search depends on guessing the right words.

**What happened when we tried it.** We ran that exact sentence against this project's copy of OIG's recommendations three ways. This tests word matching on our data, not OIG's website itself.

| Approach | Result |
|---|---|
| Require every word to match | No results |
| Match any word | Led with emergency exits, hallway obstructions, and handrails |
| The assistant's search | Led with recommendations to secure medication carts |

**The difference.** The manager gets the relevant findings, each with a report number and link, without first having to learn how OIG phrases things. The top results here are from 2015 and 2016, so the natural next step is to narrow to recent inspections. Results are not always this clean, which is why a person should check them against the cited reports.

## Use case 2: Preparing for an inspection

**The situation.** A manager at the VA El Paso Healthcare System asks: "Help me prepare for our next inspection."

**Using the website.** The manager can pull up El Paso's reports and filter peer reports by type and date. The findings are visible there, but what each facility committed to do is in its PDF. Comparing even a dozen peers means opening a dozen PDFs.

**Using the assistant.** One conversation can bring together:

- **The facility's own history:** prior findings, whether they closed, and anything cited in more than one report.
- **What peers were cited for:** recurring findings under the current inspection program, and how common each one is.
- **What peers did about it:** their committed corrective actions and target dates.
- **A realistic timeline:** how long that kind of finding has typically taken to close.
- **The likely timing:** an estimated next inspection window, labeled as an estimate, because OIG publishes no schedule.

Here is what sits behind that. El Paso's July 2026 report (25-00193-155) includes the open recommendation that leaders "ensure staff maintain a clean and safe environment." The facility's written response, including whether it agreed, its target date, and its planned actions, appears only in the PDF. Once extracted, it can sit alongside what peers committed to for the same finding.

Peer findings can be searched today. The rest of this list arrives with the data build described under "Where it stands today."

**The difference.** The manager starts from an evidence-based checklist instead of a blank page.

## Use case 3: Reading a trend honestly

**The situation.** A VISN patient safety officer asks whether communicating test results to patients is still a problem.

**Using the website.** The officer can repeat a search for each year and tally the totals by hand, which gives counts but no context.

**Using the assistant.** One question returns the table. These are recommendations containing the words "communicating test results":

| Year report was published | Reports | Recommendations | Still open |
|---|---|---|---|
| 2022 | 3 | 4 | 0 |
| 2023 | 3 | 3 | 0 |
| 2024 | 1 | 1 | 0 |
| 2025 | 21 | 26 | 7 |
| 2026 (to date) | 28 | 41 | 25 |

Taken alone, that looks like a problem that suddenly got much worse. The data supports a second reading. Nearly all of the 2025 and 2026 reports come from one inspection series, Healthcare Facility Inspections, which grew from 6 reports in 2024 to 59 so far in 2026, and 28 of those 59 contain this finding. So the jump may reflect a real problem, or a newer program that looks for it and is reporting far more often.

**The difference.** The data cannot say which reading is right, so the assistant gives the counts and both readings rather than choosing one. The officer gets a useful number, 28 of 59 inspections this year, and a better question: is this a gap in our facilities or a change in what is being measured? Recent years also show more open items partly because those findings have had less time to close.

## Where it stands today

| Status | Capability |
|---|---|
| **Working now** | Plain-language search of findings; full report details; counts and trends by year; open-item aging by office, topic, or report type |
| **Built, waiting on data** | Corrective actions and target dates from PDFs; facility profiles and repeat findings; recurring-finding groups; time to close; promised versus actual dates |
| **Not built yet** | An inspection readiness brief that brings these together for one facility |
| **Not yet done** | Formal accuracy testing, and connecting it to a hosted assistant. It currently runs on one computer |

Search quality is good on many topics and uneven on others, and near-identical findings can crowd the top of the results. Treat the results as a strong starting point, and do not treat a search shortlist as a count. Statuses can also change after the data is collected, which is why each answer states its date.
