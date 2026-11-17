# Lessons learned

*A running record of what testing found, what changed, and what it taught, newest first. Each entry names its evidence in [`eval/results/`](../eval/results/). The scores themselves are in [testing-results.md](testing-results.md); the method is in [testing-architecture.md](testing-architecture.md).*

The server is the subject of every test. The models that call it are instruments: a strong model shows what the server makes possible, and a weaker one shows where the server must carry more of the load. So most lessons below end in a server change, not a prompt change.

## November 17, 2026: security review and robustness

**Ask for a review that is not anchored on your own.** A separate review agent read the code without the builder's conclusions. It found what the builder's own tests had missed: tool arguments were traced before validation, so one client could send oversized calls and push every earlier trace out of the store, and nothing limited how many upstream requests a burst of tool calls could start. Both are fixed, each with a test. *Record: [SECURITY.md](../SECURITY.md).*

**Bound what a caller can make the server do, not only what it can ask.** The rate limit counted requests, but one inspection brief starts up to fourteen upstream requests. A limit on upstream requests in flight, eight per process, now caps the work behind any burst.

**An error a caller can trigger must stay clean.** An 8,000-item status list made a request too long to send; the client got a raw message and the log got a long stack trace. Lists, offsets, and resource names are now bounded, and an unsendable request is a clean error with a hint.

**Tell the client what to do and the operator why.** The hint for an unreachable data API named settings and how the API runs. The client now gets "retry once, then say the data could not be reached"; the setup detail goes to the operator's log.

**Test hostile input against the running server, not only in unit tests.** A robustness check sends every tool traversal, injection, and out-of-bounds values, then bursts past the rate limit and the data API's search slots, and inspects every reply for stack traces, addresses, and credentials. It passed 43 of 43 before and after the hardening, and runs against every deployment.

**Least privilege costs little in a container.** Dropping every Linux capability, a read-only filesystem, and memory and process limits needed no code change, and every check still passed.

## November 17, 2026: the Orchestrate runs, the baseline, and the adversarial set

**A weaker model is the better test of a server.** IBM's agent in watsonx Orchestrate runs GPT-OSS 120B. Across 72 answers (24 questions, three runs) it passed 8 to 11 of 24 per run on the project's scoring, where Claude Opus 5.5 passes 23. Reading every failure against the tool results sorted them by cause. Some were the model's alone: it read 2024 as the peak year from a table that showed 2015, and it rarely gave a report number with its link. Others were the server's, exposed only because this model used the tools differently, and those are the ones worth fixing. *Evidence: `2026-11-17-orchestrate/summary.md`.*

**A filter that matches nothing must say so.** The agent passed "Office of Information and Technology" where the data uses "Information and Technology (OIT)", and put "Veterans Benefits Administration" in the inspection domain filter. Both returned empty results without complaint, and the agent told the user there was no data. This is the same failure as "NY" for New York (November 16). The server now converts every office's full name to its abbreviation, refuses an office in the domain filter and names the right filter, and adds a notice to any empty analysis saying to check the filter values first. *Change: [#60](https://github.com/HacksterT/oig-mcp/pull/60).*

**Precompute what a question usually asks.** Asked for the year with the most recommendations, the agent misread a 31-row table in all three runs. The year analysis now names its peak year. A field costs little and removes a reading task that a weaker model gets wrong. *Change: #60.*

**An error hint must match its cause.** A data API failure (status 500) reached the agent with the hint "the data API is not reachable", and it gave up. Failures now get their own hint: retry once, then try other filters, and say the part could not be retrieved rather than giving a number. *Change: #60.*

**Weaker models find bugs stronger ones never trigger.** The Orchestrate agent sent filter combinations no Claude run had used, and one exposed a data API bug: counting with only a facility-response or domain filter failed with a 500. *Change: oig-data-source #38; the four failing requests now return 200.*

**Correlate with server-side traces before blaming the server.** The evaluator on IBM's virtual machine reported "tool timeouts." The data API's traces showed every call that reached it succeeded, the slowest in about 1.5 seconds. The errors were Orchestrate's own: two "MCP server is starting up / token has expired" messages and one internal "connection refused", plus one connection that dropped before reaching the data API. The fix was operational, logging in again before each run, not a server change.

**Check the scorer against each new model's output.** GPT-OSS 120B writes report numbers with non-breaking hyphens ("25‑00193‑155"). The code checks missed every one, which looked like a citation failure. The scorer now reads typographic hyphens and spaces as plain ones, and every earlier run was rescored to confirm no result changed.

**Measure the server against no server.** The hackathon's sample evaluation recommends a no-tool baseline, and the project had none. With no tools, Claude Opus 5.5 passed 3 of 24 questions and Llama 3.3 70B passed 2; Opus gave the exact figure on 1 of 16 fact questions and Llama on none. With the server, before the November 17 fixes, they passed 23 and 9. The questions they passed without tools were refusals, which need no data. *Evidence: `2026-11-17-baseline-*-no-tools`.*

**The server's scope belongs in the server.** Six adversarial questions were added: an instruction to ignore the rules and rank facilities, an instruction injected into pasted text, a report number that does not exist, a medical emergency, a request to name employees, and a question outside OIG's data. With the server, Opus passed 5 of 6 (it gave aspirin dosing) and Llama 3.3 70B passed none: it guessed a station number and reported 0 open recommendations, summarized another report in place of the missing one, and treated out-of-scope questions as unclear. The server's instructions now state its scope (no medical, benefits, or legal advice; an emergency goes to 911; never guess who was responsible), the not-found reply says not to substitute another report, and the station filter says to look a station up rather than guess. Afterward Opus passed 6 of 6 and Llama 4 of 6, with the model unchanged; Llama still missed the emergency direction and the out-of-domain question. These runs are not blind: the questions and the fixes were written the same night. *Evidence: `2026-11-17-adversarial-*`.*

**Check a claim against the data before the server makes it.** The first version of that scope line said the data names no employees. A query of the snapshot found 77 recommendations that do, mostly in administrative investigations ("take the appropriate action against" a named official). The line now says inspection findings are addressed to roles and offices, never to guess who was responsible, and to name a person only where a quoted finding does, with its citation.

**Keep every result within a smaller model's context.** Rerun on the 24 questions, Llama 3.3 70B stopped on the Durham question: its tool results had reached 139,912 tokens, past the model's 131,072. A facility profile with 100 recommendations was about 85,000 characters, and each recommendation repeated its report's title, type, and path, which the profile's report list already carries. Those repeats are gone, which cuts a full page by about a quarter, and the page-size field says counts and the full report list come with any page size. It was not enough: on the next run the same question reached 137,755 tokens. Finding which results add up to that is open. A server tested only with a large-context model can look efficient when it is not.

**A fix for one question can move others.** After the November 17 changes, Llama 3.3 70B still passed 9 of 24: two questions it had failed now pass, and two it had passed now fail, while tool choice (17 to 19 of 20), citations (1 to 3 of 8), and data dates (1 to 3 of 5) improved. A total alone would have hidden both the gains and the losses.

**One failed question should not end a run.** The harness stopped the whole Llama run on that one error. A question that fails now records an empty answer with its error, and the run goes on.

**Rerun the strongest model after every server change.** The changes above were made for weaker models. Claude Opus 5.5 was rerun on all 24 questions afterward: 23 of 24, every measure unchanged, so the fixes cost the strong model nothing.

**Three readings settle more than one.** Each Orchestrate run was read by IBM's evaluation engine, by the project's scoring with a Claude judge, and by the same scoring with an IBM watsonx.ai judge. The two judges gave the same pass or fail on 67 of 71 answers. IBM's engine agreed with the project's scoring on 52 of 72; it passed 16 the project failed, mostly because it scores the whole conversation and has no citation or data-date check. Neither reading alone would have shown that.

**Shared limits make concurrent test runs interfere.** A local run overlapping the Orchestrate runs pushed the data API past its four concurrent searches and drew a 503. Test runs against the shared data API now run one at a time.

## November 16, 2026: deployment in watsonx Orchestrate

**A place name is not a facility name.** Asked what OIG found at "the New York VA", the agent searched for findings filtered to state "NY", matched nothing, and reported no findings. The facility lookup matched only text in a facility's name, and the state filter expected "New York." The server now routes place questions to the facility tool, retries a lookup without generic words, and accepts postal codes. *Change: [#37](https://github.com/HacksterT/oig-mcp/pull/37).*

**A test should expect only the critical path.** A saved Orchestrate test expected every tool call its recording made, and failed when the agent answered correctly with fewer. Tests now name only the call each question depends on.

**A deployment must carry its configuration explicitly.** The first Orchestrate registration ran the server with no data API address. The toolkit now passes the data API's settings through an Orchestrate connection. *Change: [#35](https://github.com/HacksterT/oig-mcp/pull/35).*

**Build reproducibly across machines.** The image built on IBM's virtual machine could not import the server because of that machine's file permissions. Files in the image are now made readable whatever the build machine's settings. *Change: [#33](https://github.com/HacksterT/oig-mcp/pull/33).*

## November 4 to 10, 2026: the first evaluation runs

**Guidance has to reach the model.** FastMCP drops a tool docstring's Returns section before sending it, and the hints steering a model to the right tool were there. They moved into the description proper. *Change: [#30](https://github.com/HacksterT/oig-mcp/pull/30).*

**Do not return a number the data cannot support.** Claude Sonnet 5.5 gave "about 86%" as a deadline miss rate while warning against it. The analysis tool no longer returns the counts that invite that rate.

**Do not rely on a host to pass the server's instructions.** DeepSeek through Hermes Agent gave report numbers without links; its host did not pass the server's instructions to the model. Each tool result now carries its own citation line.

**Name what a result covers.** Hermes Agent matched parallel results to VISNs by position and summed rows that overlap. Analysis results now echo their filters and say what a VISN or state filter leaves out.

**Keep a failure a failure.** The one Claude failure is a scoring call on a correct answer. The scorer was not changed after seeing it, so the result stays honest.
