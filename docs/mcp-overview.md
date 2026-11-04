# MCP Exec Summary: VA OIG Recommendations Assistant

*For leaders and staff. Status and figures as of November 4, 2026.*

## In brief

The VA Office of Inspector General (OIG) has published thousands of reports. Its website is good at finding a document. It is not built to answer a question that spans many documents, such as "what keeps being cited?" or "what did other facilities commit to do about it?" Today, answering those questions means hours of reading reports and PDFs.

This project connects an AI assistant to a structured copy of what OIG publishes, currently 4,410 reports, 15,649 recommendations, and 11,264 facility responses drawn from report PDFs. Staff ask a question in plain language and get an answer drawn from across all of them, with a report number and link for every finding. The connector is called an MCP server, which is simply a standard way for an AI assistant to use an outside data source.

It uses only public information from vaoig.gov and no internal VA systems. It is not an official VA or OIG product, and it does not replace VA's own tracking of recommendations.

## Where it goes beyond OIG's website

OIG's search is solid, and this project does not try to replace it. If you know what you are looking for, the site's keywords and filters will find it, and every answer here links back to the site. The difference is in what happens after the search.

| What you need | On OIG's website | With this assistant |
|---|---|---|
| Use it directly from an AI assistant, with citations | No API or bulk export | Yes. This is the main difference, and the rest follows from it |
| Find a report or recommendation | Keywords plus filters for date, report type, topic, office, status, and location | Ask in your own words. It looks for matching meaning as well as matching words, with mixed results |
| See how an issue changes over time | One total per search, so you repeat the search for each year and tally the results | A year-by-year table from one question |
| See how old open items are | Site-wide totals in three age bands, and a filter for each band | Typical and oldest age, compared across offices, topics, or report types |
| Learn how long fixes take | A closure date on each closed recommendation, with no averages | Typical time to close, the usual range, and the share not implemented |
| See what facilities committed to do | Only in the report PDFs | Searchable commitments and target dates across reports |
| Spot what recurs across facilities | Read the reports and compare them yourself | Near-identical findings grouped, showing how many reports contain them |

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

**What happened when we tried it.** We ran that exact sentence against this project's copy of OIG's recommendations three ways on this project's data, and once on OIG's own recommendation search.

| Approach | Result |
|---|---|
| Require every word to match | No results |
| Match any word | Led with emergency exits, hallway obstructions, and handrails |
| The assistant's search | Led with recommendations to secure medication carts |
| OIG's recommendation search, same sentence | No results |

**How it compared overall.** We ran ten such questions through both searches, as full sentences and as short keywords, and compared the top five recommendations from each.

| Search | Questions with a relevant result | Relevant results, of those returned |
|---|---|---|
| The assistant's search, full sentence | 8 of 10 | 22 of 50 |
| The assistant's search, short keywords | 7 of 10 | 17 of 50 |
| OIG, short keywords | 6 of 10 | 14 of 28 |
| OIG, full sentence | 0 of 10 | No results on any |

Treat this as directional. The test is small, an AI judged relevance rather than a person, and we wrote the questions knowing how this project performed, so they favor it. OIG lists results newest first, so its top five are its newest matches, not necessarily its best. Corrective actions were not judged.

**The difference.** The gain is reach and access, not sharper results. The manager can use their own words and still find something, without first learning how OIG phrases things. A full sentence here was relevant 44 percent of the time, close to the 50 percent for OIG's short keywords, and on identical keywords OIG's did better, at 50 percent against 34. On two of the ten questions, no search found anything relevant. So results still need checking against the cited reports. The larger difference is that an AI assistant can search, count, and compare the whole record, and cite each result.

## Use case 2: Preparing for an inspection

**The situation.** A manager at the VA El Paso Healthcare System asks: "Help me prepare for our next inspection."

**Using the website.** The manager can pull up El Paso's reports and filter peer reports by type and date. The findings are visible there, but what each facility committed to do is in its PDF. Comparing even a dozen peers means opening a dozen PDFs.

**Using the assistant.** One request brings together:

- **The facility's own history:** prior findings, whether they closed, and anything cited in more than one report.
- **What peers were cited for:** recurring findings under the current inspection program, and how common each one is.
- **What peers did about it:** their committed corrective actions and target dates.
- **A realistic timeline:** how long that kind of finding has typically taken to close.
- **The likely timing:** an estimated next inspection window, labeled as an estimate, because OIG publishes no schedule.

These are real records. The most common recurring finding in current inspections, on developing workflows for communicating test results, appears in 21 of the 112 Healthcare Facility Inspection reports. El Paso's July 2026 report (25-00193-155) includes the open recommendation that leaders "ensure staff maintain a clean and safe environment." The facility concurred, set a target of January 29, 2027, and described its cleaning inspections and procedures. That response appears only in the PDF, and it can now sit alongside what peers committed to for the same finding. El Paso's next inspection window is estimated at about January 2028.

**The difference.** The manager starts from an evidence-based checklist instead of a blank page.

## Use case 3: Reading a trend honestly

**The situation.** A VISN patient safety officer asks whether communicating test results to patients is still a problem.

**Using the website.** The officer can repeat a search for each year and tally the totals by hand, which gives counts but no context.

**Using the assistant.** One question returns the pattern. These are reports with recommendations that mention test or laboratory results:

| Years | Reports per year |
|---|---|
| 2015 and 2016 | 32 and 27 |
| 2017 through 2024 | 2 to 11 |
| 2025 and 2026 (to date) | 21 and 28 |

Taken alone, that looks like facilities improved and then slipped. The data cannot support that by itself. Nearly all of the 2025 and 2026 reports come from one inspection series, Healthcare Facility Inspections, where this finding appears in 20 of 45 reports in 2025 and 28 of 61 so far in 2026. OIG inspects against a protocol, so the rise could reflect the topic returning to that protocol as much as any change in care, and the same goes for the earlier drop.

**The difference.** The data cannot say which reading is right, so the assistant gives the counts and both readings rather than choosing one. What the counts do show is useful either way: this is a live inspection theme now, and a patient safety manager should be ready for it.

## Where it stands today

| Status | Capability |
|---|---|
| **Working now** | Plain-language search of findings and corrective actions; full report details; facility profiles and repeat findings; recurring-finding groups; counts and trends by year; time to close and open-item aging by office, topic, or report type; a one-step inspection brief for a facility |
| **Tested** | 24 questions scored against answers computed from the data, on two AI models. Each passed 23, with no made-up report numbers. The test is small, and its authors wrote the questions, so see the [evaluation](evaluation.md) for its limits. An independent agent's answers are in the [test bank](https://www.troymd.com/mcp-hackathon-test-bank) |
| **Not yet done** | Connecting it to a hosted assistant. It currently runs on one computer |

Search results are mixed: fewer than half were relevant in the small test above, results vary by topic, and near-identical findings can crowd the top. Treat results as a starting point to check, and do not treat a search shortlist as a count. Statuses can also change after the data is collected, which is why each answer states its date.

Closure dates need care. A closure date appears to record when OIG closed a recommendation after reviewing evidence, not when the work finished. So time to close describes OIG's process as well as the facility's, and this project does not report whether facilities met their target dates.
