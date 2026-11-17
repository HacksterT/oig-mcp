# Office hours: questions, answers, and decisions

A running record. Each question says why it matters; once answered, the answer and what it changed sit beside it, and the open questions stay in place for the next session. Newest answers first in each section. The submission is due November 20, 2026.

## What the November 17 GSA office hours settled

| Topic | Answer | What it changes |
|---|---|---|
| The demo | A video, YouTube style: narrated, telling a story, **3 minutes or under**. It shows one use case. | The demo is a scripted, voiced video of one use case, not a screen tour. |
| Live access | The demo replaces judges' need to reach the MCP server live. Judges assess the code in the repository but are unlikely to call the server. | The video and the repository carry the evaluation. The hosted endpoint stays up but is not on the critical path. |
| Where the server runs | Anywhere, as long as the repository explains it and security is addressed. The Cloudflare design was accepted. | No move to another host is needed. |
| watsonx Orchestrate | Expectations for using it are liberal. | Orchestrate results are reported as they are; no further time goes to tuning the agent for its score. |
| The data pipeline repository | It stays private. Recommended: show how it is built with a figure in the deck. | Add an architecture figure, data pipeline to data API to MCP server to hosts, to the deck. [data-pipeline.md](data-pipeline.md) remains the written account. |
| The deck | It should complement the demo video, not repeat it. Screenshots are welcome, for example of MCP features. | Fewer words, more figures and screenshots; the deck covers what the video cannot show in three minutes. |
| stdio and Streamable HTTP | Keeping both transports is fine. | Say plainly in the README which transport serves which client, without adding a new document. |

## Decisions that follow

- **Use case for the demo:** preparing for an OIG inspection at the James H. Quillen VA Medical Center, Mountain Home, Tennessee: a short architecture introduction, then a role-played preparation in a few questions.
- **Platform for the recording:** open. Orchestrate, Hermes Agent, and Claude Desktop are the candidates. This is the first decision, because the script depends on it.
- **MCP features in the demo or deck:** elicitation is new, and hosts handle it differently: in testing, no host showed the server's own form, but after the server's result said to ask, Hermes offered the facilities as choices with its own tool and Claude Desktop asked in chat. That difference is a finding to show, not a defect to hide.

## For the organizers and judges

### Answered

1. **What is judged: the MCP server alone, or also its deployment on the partner platform?** The code in the repository, the demo video, and the deck. Expectations for Orchestrate are liberal. *(November 17)*
2. **Will judges run the server?** Unlikely: the demo video stands in for live access. The hosted endpoint ([testers.md](testers.md)) and the section where anyone can recompute every saved score stay available. *(November 17)*
3. **Is it acceptable that the data pipeline is in a separate private repository?** Yes. Recommended: an architecture figure in the deck. *(November 17)*
4. **Formats and limits:** the demo is a narrated video of 3 minutes or under, and the deck should complement it, screenshots welcome. *(November 17)* Still open:
   - The deck's format (.pptx, PDF, or Google Slides) and any slide limit.
   - Whether the video is embedded or a separate file, and where it is hosted.
   - The evaluation document's format: Word, PDF, or Markdown in the repository.
5. **Can the server run anywhere, and is the security design acceptable?** Yes, if the repository explains it and security is addressed; the Cloudflare design was accepted. *(November 17)*
6. **Is keeping both stdio and Streamable HTTP acceptable?** Yes; the README should say which serves which client. *(November 17)*

### Still open

1. **What time and time zone is the November 20 deadline, and how is it submitted?** Is the repository judged at a tagged commit, or as it stands at judging time? The final evaluation ran at tag `eval-final-1`.
2. **Is there a live presentation at the closing ceremony on December 16 or before?** The demo is recorded either way.
3. **Do judges value newer MCP features?** The server offers argument completions and asks the user to choose when a facility name is ambiguous (elicitation, on both protocol versions). How much of the deck and video should they take?
4. **For criterion 2, is our evaluation design what you are looking for?** Gold answers computed by SQL, a no-tool baseline, five models, two judges from different model families, IBM's evaluation engine, an adversarial set, a failure analysis, a load test to 40 concurrent clients, tests in real hosts, and scores anyone can recompute. Is anything missing, such as a human review of answers?
5. **Does the security section need anything beyond the sample's, such as an SBOM or a threat model?** Ours has an independent review, a robustness check of 48 hostile inputs run against every deployment, and a hardened container.

## For IBM

### What testing has shown

- **Elicitation in Orchestrate:** asked about "the New York VA" in round 2, the agent showed no form; it listed the New York facilities in text and asked which one, as the server's result says to. Asked about "the California VA", it did not call the facility tool at all: it searched for findings across California and returned example reports. *(November 17, Orchestrate round 2, step 2b)*
- **Updating a toolkit:** re-importing still removes its tools from the agent, and they are added back by hand. *(November 17)*

### Still open

1. **Which MCP protocol version does Orchestrate negotiate, and does it advertise elicitation?** No form appeared in testing, which suggests it does not. On 2026-07-28 the server asks with an `input_required` result (SEP-2322); on earlier versions it asks within the call. One desktop host we tested claims elicitation on 2026-07-28 but fails when that result arrives.
   - **Does it support progress notifications, argument completions, and resource links in tool results?**
   - **Does process-per-invocation mean a new server process for every tool call?** If so, no state or connection pooling in the server carries across calls.
2. **Does Orchestrate use an MCP server's resources and prompts, or only its tools?** The server also offers three resources and two workflow prompts.
3. **Can judges be given access to see the deployed agent?** Less important now that the demo video stands in for live access.
4. **Can a toolkit be updated in place,** without re-adding its tools to the agent by hand?
5. **Is there a limit on the size of a tool result, and are large results truncated before the model sees them?** Our largest result, a 100-item facility profile, went from 70,126 to 40,906 characters after it overflowed a 128K-context model. Silent truncation would still change answers without any sign.
6. **Which models can an agent use in the hackathon instance besides gpt-oss-120b?**
7. **ADK evaluations:** can journey success score only the agent's first reply; can the judge model be chosen; how to avoid "token has expired" partway through a run (we now log in again before each run)?
8. **Are the runtime errors we saw known issues?** Expired-login errors and one internal connection failure in 4 of 72 conversations in round 1.
9. **Can tool-call logs or traces be exported from Orchestrate for evaluation?** Today we match conversations to our data API's traces instead.
10. **Can a remote MCP toolkit (Streamable HTTP) authenticate with a bearer token through a connection?**
11. **Would a second Orchestrate agent that calls ours count as a creative agent workflow?**
