# oig-mcp wiki

The documentation for **oig-mcp**, an MCP server that lets AI assistants answer questions across VA Office of Inspector General (OIG) reports and recommendations, with a report number and link for every finding. It was built for the GSA MCP Server and AI Agent Government Hackathon (Dataset Access track), on IBM watsonx Orchestrate.

The [repository README](../README.md) is the short overview and quick start. This wiki is the full account: read it in order as a book, or go straight to a page.

## Pages

| Section | Page | What it covers |
|---|---|---|
| **Overview** | [Mission and use cases](overview/mission.md) | The problem, who it serves, and what changes for them |
| | [Glossary](overview/glossary.md) | OIG, VISN, HFI, elicitation, and the other terms used here |
| **Architecture** | [System](architecture/system.md) | Both repositories end to end, transports, hosting, Orchestrate |
| | [Data source](architecture/data-source.md) | The private pipeline that builds and checks the data |
| | [Data API](architecture/data-api.md) | The contract the server relies on |
| | [Server design](architecture/server-design.md) | Tools, resources, prompts, request flow, and design rules |
| | [MCP features](architecture/mcp-features.md) | Elicitation, completions, output schemas, provenance, and host support |
| **Guides** | [Connecting](guides/connecting.md) | Each host, over stdio or HTTP |
| | [Tools](guides/tools.md) | The seven tools, when to use each, and their inputs |
| | [Deployment and operations](guides/deployment.md) | Where it runs, how each deployment is checked, day-to-day operation |
| | [Decisions](guides/decisions.md) | What was chosen, why, and what it costs |
| **Evaluation** | [Method](evaluation/method.md) | How the server is tested, and how to verify every score yourself |
| | [Results](evaluation/results.md) | Every score with its limits, and the round-by-round journey |
| | [Debrief](evaluation/debrief.md) | Did the changes help, and how much weight the evidence bears |

## For the hackathon submission

The deck, the evaluation document, and the video script are drawn from these pages: [submission/deck.md](submission/deck.md), [submission/evaluation-document.md](submission/evaluation-document.md), and [submission/video-script.md](submission/video-script.md); [submission/render/](submission/render/README.md) builds the DOCX and PPTX files from them. Security, with every check and the independent review, is in [SECURITY.md](../SECURITY.md) at the repository root. Earlier working documents are kept, unchanged, in [`_archive/`](_archive/README.md).

## Conventions

Every figure in this wiki traces to a file in [`eval/results/`](../eval/results/), a command anyone can rerun, or a pull request. Data figures are from the build of November 4, 2026; evaluation figures are as of November 17, 2026.
