# Video script (draft)

*The demo video for the GSA hackathon: narrated, 3 minutes or less, one use case. GSA's guidance: the video replaces judges using the server live, and the deck complements it. Narration runs about 150 words a minute, so the whole script stays under 450 words. Lines in quotation marks are narration; the rest is what is on screen.*

**Use case:** preparing for an OIG inspection at the Mountain Home VA (James H. Quillen VA Medical Center, station 621).

---

## 1. The problem (0:00 to 0:25)

**On screen:** vaoig.gov. A search for "Mountain Home" returns a list of report PDFs.

"The VA Inspector General has published more than four thousand reports. If you run a VA medical center and want to know what OIG has found there, and what it finds at places like yours, you open these PDFs one at a time."

## 2. The server (0:25 to 0:45)

**On screen:** the architecture figure from the deck (slide 5).

"This is an MCP server: it gives any AI assistant tools over every OIG report and recommendation, with a citation for every finding. It runs in IBM watsonx Orchestrate, Claude, and any MCP client."

## 3. Asking, not guessing (0:45 to 1:25)

**On screen:** the Claude Code recording. The question is typed; the pick-list appears; one facility is chosen; the answer opens with "the one you picked".

"Here is a question with a trap: there are three Columbia VAs. Most AI assistants would just pick one, and findings from the wrong facility would be credited to the one you meant. So the server never lets the AI guess. Where the app supports it, the server asks you directly, with a pick-list. That is MCP elicitation."

**On screen:** the elicitation chart (deck slide 9).

"Compared with the AI asking in chat, the pick-list takes half the back-and-forth and 39 percent fewer tokens. And we learned one thing building it: when the server asks the user, it must also tell the AI what the user decided. Until we added one line saying 'the user chose this facility', Claude treated the pick as a guess and offered the others."

## 4. The inspection brief (1:25 to 2:15)

**On screen:** "Help me prepare for the next OIG inspection at the Mountain Home VA." The inspection brief: open findings, repeat findings, the estimated next inspection window, what peer facilities committed to do, each with a report link.

"Now the use case. One question, and one tool call gathers what a quality manager would spend days assembling: [read the two or three most useful items from the recorded answer]. Every item links to the OIG report it came from."

## 5. Knowing what not to answer (2:15 to 2:35)

**On screen:** "Which VA facility is the worst?" The assistant declines and offers what the data can support.

"And it knows its limits. It will not rank facilities, give medical advice, or guess who was responsible."

## 6. Does it work? (2:35 to 3:00)

**On screen:** the five-models chart (deck slide 14), then the repository.

"We tested it with five AI models from four companies, against answers computed directly from the data. Without the server, models got 2 or 3 of 24 questions right. With it, 9 to 23, and that spread taught us the most: weaker models need the server to do more of the work, and every fix we made for them made the server better for all of them. Every score is in the public repository."

---

## Recording notes

- **Section 3:** the Columbia take is recorded. If you re-record, "the Tennessee VA" fits the use case better: it matches Memphis, Mountain Home, and Tennessee Valley, and choosing Mountain Home leads straight into section 4.
- **Sections 4 and 5:** record in the same host as section 3, so the video shows one app.
- **Never on screen:** `/mcp` or `claude mcp list` output (local paths), `.env`, trace files, Cloudflare dashboards.
- **Numbers used:** 2 or 3 of 24 and 9 to 23 ([Results](../evaluation/results.md)); half the back-and-forth and 39 percent fewer tokens ([What the form saves](../evaluation/results.md#what-the-form-saves)).
