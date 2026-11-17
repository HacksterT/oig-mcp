# Office hours questions, November 17, 2026

Questions to ask, most important first in each group. Each line says why it matters, so the answer can be applied the same day.

## For the organizers and judges

1. **What exactly is judged: the MCP server alone, or also its deployment on the partner platform?** It decides how much of the last three days goes to the server versus watsonx Orchestrate.
2. **Will judges run the server, or judge from the repository, the deck, and the evaluation document?** If they run it, we need a token handoff for the hosted endpoint and a short "verify it yourself" guide. If not, the evaluation document carries the weight.
3. **Is it acceptable that the data pipeline is in a separate private repository, with the MCP server repository public?** If the pipeline must be visible, we publish a description of it or make it public before submission.
4. **What are the formats and limits for each deliverable?**
   - The deck: .pptx, PDF, or Google Slides, and is there a slide or length limit?
   - The demo: an embedded video or a separate file, and a maximum length?
   - The evaluation document: Word, PDF, or Markdown in the repository?
5. **When exactly is the deadline (date, time, and time zone), and how is it submitted?** Is the repository judged at a tagged commit, or as it stands at judging time?
6. **Is there a live presentation or demo, at the closing ceremony on December 16 or before?** It decides whether the demo must work live or can be recorded.
7. **Do judges value newer MCP features (elicitation, argument completions, resource links in results), or core tools done well?** It decides whether to spend about four hours on them.
8. **For criterion 2, is our evaluation design what you are looking for?** Our design: gold answers computed by SQL, a no-tool baseline, five models, two judges from different model families, IBM's evaluation engine, an adversarial set, and a failure analysis. Is anything missing, such as a load test or a human review of answers?
9. **Does the security section need anything beyond the sample's, such as an SBOM or a threat model?**

## For IBM

1. **Do local (stdio) MCP toolkits in Orchestrate support MCP client features?** In particular elicitation (the server asks the user to choose), progress notifications, argument completions, and resource links in tool results. Answers decide whether we build elicitation for ambiguous facility names this week.
2. **Does Orchestrate use an MCP server's resources and prompts, or only its tools?** The server also offers three resources and two workflow prompts.
3. **Once a toolkit is imported, can any agent in the instance use its tools, and can judges be given access to see the deployed agent?** It decides how the Orchestrate deployment is shown to judges.
4. **Can a toolkit be updated in place?** Re-importing ours removed its tools from the agent, and they had to be added back by hand each time.
5. **Is there a limit on the size of a tool result, and are large results truncated before the model sees them?** One of our questions produced about 137,000 tokens of tool results on a 128K-context model. We are trimming results this week.
6. **Which models can an agent use in the hackathon instance besides gpt-oss-120b?** Running the same agent on two or three models would show whether failures come from the server or the model.
7. **ADK evaluations:**
   - Can journey success score only the agent's first reply, without the simulated user?
   - Can the judge model be chosen?
   - How do we avoid "token has expired" partway through a run?
8. **Are the runtime errors we saw known issues?** We saw expired-login errors and one internal connection failure in 4 of 72 conversations. Is there anything we should do to avoid them?
9. **Can tool-call logs or traces be exported from Orchestrate for evaluation?** Today we match conversations to our data API's traces instead.
10. **Can a remote MCP toolkit (Streamable HTTP) authenticate with a bearer token through a connection?** This is the alternative to the local toolkit, and it would let Orchestrate use the same hosted server other clients use.
11. **Would a second Orchestrate agent that calls ours be seen as a creative agent workflow, or as outside the MCP server being judged?** For example, an inspection-prep agent handing off to a checklist agent.
