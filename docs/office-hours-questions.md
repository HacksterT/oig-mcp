# Office hours questions

Questions to ask, most important first in each group. Each line says why it matters, so the answer can be applied the same day. First written for November 17 and updated the same day with what testing has since shown: where testing answered part of a question, that part is stated, and only what is still open is asked. The submission is due November 20, 2026.

## For the organizers and judges

1. **What exactly is judged: the MCP server alone, or also its deployment on the partner platform?** It decides how the last days split between the server's documents and the watsonx Orchestrate results.
2. **Will judges run the server, or judge from the repository, the deck, and the evaluation document?** Both are ready: a hosted endpoint with tokens issued per tester ([testers.md](testers.md)), and a "Verify it yourself" section in the evaluation document that recomputes every saved score with no keys. If judges run it, how should tokens reach them?
3. **Is it acceptable that the data pipeline is in a separate private repository, with the MCP server repository public?** Its work is now described stage by stage, with its checks and figures, in [data-pipeline.md](data-pipeline.md). Is that enough, or must the pipeline's code be visible?
4. **What are the formats and limits for each deliverable?**
   - The deck: .pptx, PDF, or Google Slides, and is there a slide or length limit?
   - The demo: an embedded video or a separate file, and a maximum length? Ours is planned at under four minutes.
   - The evaluation document: Word, PDF, or Markdown in the repository?
5. **What time and time zone is the November 20 deadline, and how is it submitted?** Is the repository judged at a tagged commit, or as it stands at judging time? The final evaluation ran at tag `eval-final-1`.
6. **Is there a live presentation or demo, at the closing ceremony on December 16 or before?** It decides whether the demo must work live or can be recorded.
7. **Do judges value newer MCP features?** The server now offers argument completions for facility names and topics, and asks the user to choose when a facility name is ambiguous (elicitation, on both protocol versions). Should the deck give these a slide, or keep the focus on the core tools?
8. **For criterion 2, is our evaluation design what you are looking for?** It has gold answers computed by SQL, a no-tool baseline, five models, two judges from different model families, IBM's evaluation engine, an adversarial set, a failure analysis, a load test to 40 concurrent clients, tests in real hosts, and scores anyone can recompute. Is anything missing, such as a human review of answers?
9. **Does the security section need anything beyond the sample's, such as an SBOM or a threat model?** Ours has an independent review, a robustness check of 48 hostile inputs run against every deployment, and a hardened container.

## For IBM

1. **Do local (stdio) MCP toolkits in Orchestrate support MCP client features?** We will see one answer in chat during our second round: if Orchestrate supports elicitation, asking about "the New York VA" shows a form listing the facilities. What chat cannot show:
   - **Which MCP protocol version does Orchestrate negotiate?** On 2026-07-28 the server asks with an `input_required` result (SEP-2322); on earlier versions it asks within the call. One desktop host we tested claims elicitation on 2026-07-28 but fails when the result arrives, so the answer decides which path Orchestrate users get.
   - **Does it support progress notifications, argument completions, and resource links in tool results?**
   - **Does process-per-invocation mean a new server process for every tool call?** If so, no state or connection pooling in the server carries across calls.
2. **Does Orchestrate use an MCP server's resources and prompts, or only its tools?** The server also offers three resources and two workflow prompts.
3. **Once a toolkit is imported, can any agent in the instance use its tools, and can judges be given access to see the deployed agent?** It decides how the Orchestrate deployment is shown to judges.
4. **Can a toolkit be updated in place?** Re-importing ours still removes its tools from the agent, and they have to be added back by hand each time.
5. **Is there a limit on the size of a tool result, and are large results truncated before the model sees them?** We cut our largest result, a 100-item facility profile, from 70,126 to 40,906 characters after it overflowed a 128K-context model, so this matters less than it did. Silent truncation would still change answers without any sign.
6. **Which models can an agent use in the hackathon instance besides gpt-oss-120b?** Running the same agent on two or three models would show whether failures come from the server or the model.
7. **ADK evaluations:**
   - Can journey success score only the agent's first reply, without the simulated user?
   - Can the judge model be chosen?
   - How do we avoid "token has expired" partway through a run? We now log in again before each run.
8. **Are the runtime errors we saw known issues?** We saw expired-login errors and one internal connection failure in 4 of 72 conversations in our first round. Is there anything we should do to avoid them?
9. **Can tool-call logs or traces be exported from Orchestrate for evaluation?** Today we match conversations to our data API's traces instead.
10. **Can a remote MCP toolkit (Streamable HTTP) authenticate with a bearer token through a connection?** This is the alternative to the local toolkit, and it would let Orchestrate use the same hosted server other clients use.
11. **Would a second Orchestrate agent that calls ours be seen as a creative agent workflow, or as outside the MCP server being judged?** For example, an inspection-prep agent handing off to a checklist agent.
