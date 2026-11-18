# Submission render

Scripts that turn the Markdown sources in [`docs/submission/`](../) into the files the hackathon asks for: the evaluation document as DOCX and the deck as PPTX. The Markdown stays the source of truth; edit it, then rebuild. Output goes to `out/`, which is not committed.

| Output | Source | Command |
|---|---|---|
| `out/oig-mcp-evaluation-document.docx` | [`evaluation-document.md`](../evaluation-document.md), plus three charts from [`images/`](../images/) | `uv run docs/submission/render/build_docx.py`, from the repository root |
| `out/oig-mcp-deck.pptx` | Slide text in [`build_pptx.js`](build_pptx.js); speaker notes read from [`deck.md`](../deck.md) | `npm ci && npm run deck`, from this folder |

**Requirements.** The DOCX needs [uv](https://docs.astral.sh/uv/) and [pandoc](https://pandoc.org/) 3 or later; `uv` installs `python-docx` from the script's own header, so the project's lockfile is untouched. The deck needs Node.js 20 or later.

**How they work.** `build_docx.py` points the document's repository links at GitHub so they work outside the repository, converts it with pandoc against a style sheet it writes itself, then styles the tables and adds the cover line and footer. `build_pptx.js` uses `pptxgenjs` with its own layouts and theme, native charts for every figure, and Lucide icons. The deck's slide text is shorter than `deck.md`, so a change to a figure in `deck.md` must also be made in `build_pptx.js`. Two slides hold marked placeholders for the Orchestrate screenshot and the demo video.

The structure follows GSA's sample deck and sample evaluation document from the hackathon page; the design is this project's own.
