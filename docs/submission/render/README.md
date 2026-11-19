# Submission render

Scripts that turn the Markdown sources in [`docs/submission/`](../) into the files the hackathon asks for: the evaluation document as DOCX and the deck as PPTX. The Markdown stays the source of truth; edit it, then rebuild. Output goes to `out/`, which is not committed.

| Output | Source | Command |
|---|---|---|
| `out/oig-mcp-evaluation-document.docx` | [`evaluation-document.md`](../evaluation-document.md), plus three charts from [`images/`](../images/) | `uv run docs/submission/render/build_docx.py`, from the repository root |
| `out/oig-mcp-deck.pptx` | Slide text in [`build_pptx.js`](build_pptx.js); speaker notes read from [`deck.md`](../deck.md) | `npm ci && npm run deck`, from this folder |

**Requirements.** The DOCX needs [uv](https://docs.astral.sh/uv/) and [pandoc](https://pandoc.org/) 3 or later; `uv` installs `python-docx` from the script's own header, so the project's lockfile is untouched. The deck needs Node.js 20 or later.

**How they work.** `build_docx.py` points the document's repository links at GitHub so they work outside the repository, converts it with pandoc against a style sheet it writes itself, then styles the tables and adds the cover line and footer. `build_pptx.js` uses `pptxgenjs` with its own layouts and theme, native charts for every figure, and Lucide icons. The deck's slide text is shorter than `deck.md`, so a change to a figure in `deck.md` must also be made in `build_pptx.js`. Two slides hold marked placeholders for the Orchestrate screenshot and the demo video.

The structure follows GSA's sample deck and sample evaluation document from the hackathon page; the design is this project's own.

## Picking this up

**Status (November 19, 2026).** Both files are complete. The deck has 19 slides with speaker notes, ending on a thank-you slide with the team, the links, and the submission date (November 23, 2026; change it on slide 19 if the submission goes in on another day). Slides 10 to 12 use frames from the demo video (`orchestrate-answer.png`, `demo-*.png` in `../images/`): slide 11 maps the video's six moments, and slide 12 annotates the inspection brief, so the deck carries the detail the video moves through quickly.

**Adding a screenshot.** Save the PNG in [`../images/`](../images/), then in that slide's block add `s.addImage({ path: path.join(IMG, "<file>.png"), x, y, w, h, altText: "..." })`, using the box's own x, y, and width, and a height that keeps the image's aspect ratio (slide 12 does this for `phoenix-trace.png`). For the demo, either embed a short clip with `s.addMedia({ type: "video", path, x, y, w, h })` or use screenshots. An embedded video counts toward the deck's file size, and the separate video upload is capped at 50 MB.

**Finding things in `build_pptx.js`.** Colors are the `HEX` object at the top, and the theme and fonts (Cambria headings, Calibri body) come right after it. The three slide layouts are `TITLE_DARK`, `CONTENT`, and `CONTENT_DARK`. Each slide is one `// ===== N. Name =====` block. `card`, `chip`, `iconDot`, and `numDot` draw the repeated shapes. Icons are Lucide names from `react-icons/lu`.

**Changing a figure.** Change it in the Markdown first, then in `build_pptx.js` if the slide shows it, and check the wording against the project's accuracy rules: name the model with the platform it ran on, never claim "23 of 24 on every run", and keep the limits next to the scores. The DOCX places its three charts by finding a sentence in `evaluation-document.md`. If that sentence is reworded, the build stops with an assertion that names the text it could not find; update the `figs` list in `build_docx.py` to match.

**Checking the layout.** Convert to PDF with LibreOffice and page through it: `soffice --headless --convert-to pdf out/oig-mcp-deck.pptx`, and the same for the DOCX. LibreOffice substitutes fonts for Cambria and Calibri, so spacing can shift slightly in PowerPoint and Word. Give each file a final look in Office before submitting.
