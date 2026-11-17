[Wiki](../README.md) › Overview › Mission and use cases

# Mission and use cases

*What problem the server solves, for whom, and what changes for them.*

## The problem

The VA Office of Inspector General (OIG) has published thousands of reports. Its website is good at finding one document. It is not built to answer a question that spans many documents, such as "what keeps being cited?" or "what did other facilities commit to do about it?" Those facts sit inside about 2,200 report PDFs, and answering them means hours of reading.

This project connects an AI assistant to a structured copy of what OIG publishes: 4,410 reports, 15,649 recommendations, and 11,264 facility responses drawn from report PDFs, as of November 4, 2026. Staff ask in plain language and get an answer drawn from across all of them, with a report number and link for every finding.

It uses only public information from vaoig.gov and no internal VA systems. It is not an official VA or OIG product, and it does not replace VA's own tracking of recommendations. It was built for the GSA MCP Server and AI Agent Government Hackathon, Dataset Access track, on IBM watsonx Orchestrate.

## Who it serves

| Who | What they need |
|---|---|
| Facility patient safety and quality staff | To prepare for an OIG inspection from their own history and what peers were cited for |
| Program offices and VISN leaders | To tell an isolated finding from a systemic one before choosing a fix |
| Oversight and analytics staff | Counts, trends, time to close, and the age of open items, by office, topic, or report type |

## Where it goes beyond OIG's website

OIG's search is solid, and this project does not replace it; every answer links back to it. The difference is what happens after the search.

| What you need | On OIG's website | With this server |
|---|---|---|
| Use it from an AI assistant, with citations | No API or bulk export | Yes: the main difference, and the rest follows from it |
| Find a finding in your own words | Keywords and filters | A full sentence, matched by meaning as well as words |
| See a trend over time | One total per search, tallied by hand | A year-by-year table from one question |
| See how old open items are, and how long fixes take | Site-wide age bands; a closure date per recommendation | Typical and oldest age, time to close, and the share not implemented, by office, topic, or report type |
| See what facilities committed to do | Only in the report PDFs | Searchable commitments and target dates across reports |
| Spot what recurs across facilities | Read and compare reports yourself | Near-identical findings grouped, with how many reports contain them |

The search gain is reach, not precision: in a ten-question comparison judged by AI, a full sentence here found something relevant on 8 of 10 questions, against 0 of 10 for the same sentence on OIG's search, but on identical short keywords OIG's results were more often relevant. Details: [Data source](../architecture/data-source.md#what-search-adds-and-what-it-does-not).

## Three use cases

**"Has OIG cited this?"** A patient safety manager describes a problem in their own words: "Staff left medication carts unlocked in a hallway." OIG's reports say "secure medication carts when not in use." The server's search leads with those recommendations; OIG's search, given the same sentence, returns nothing.

**Preparing for an inspection.** One request returns a facility's own history (prior findings, what closed, what was cited more than once), what peers were most often cited for under the current program, what those peers committed to do, how long such findings take to close, and an estimated next window, labeled as an estimate because OIG publishes no schedule.

**Reading a trend honestly.** Reports citing communication of test results to patients fell after 2016 and rose again in 2025 and 2026, almost all in one inspection series. The data cannot say whether facilities slipped or the topic returned to OIG's protocol, so the answer gives the counts and both readings rather than choosing one.

## Designed for trust

- **Every finding can be checked:** a report number, a vaoig.gov link, and the date the data was collected.
- **It does not rate anyone:** no facility scores, rankings, or grouping by facility.
- **It states its limits in the answer:** a repeat finding means an issue was cited again, not that nothing was done; a next-inspection date is an estimate; where a pattern has two explanations, it gives both.
- **It asks rather than guesses:** a facility name that matches several returns the matches and an instruction to ask the user.
- **Report text is a quotation, not an instruction,** and every tool only reads.

## Status

The server is complete, deployed in IBM watsonx Orchestrate, and hosted for testers at `https://mcp.troymd.com/mcp`. Without it, models answer 2 or 3 of the 24 evaluation questions; with it, from 9 (Llama 3.3 70B) to 23 (Claude). The data API runs on one machine, so it can go down; moving it to a cloud host needs no change to the server. Evaluation: [Results](../evaluation/results.md).

---

← [Wiki home](../README.md) · [Glossary](../overview/glossary.md) →
