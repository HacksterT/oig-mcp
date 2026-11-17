# What the facility form saves: five runs per arm

*November 17, 2026. Claude Opus 5.5 at medium effort through Anthropic's API, connected to the server over stdio, with the server's own instructions as the system prompt (no host context). Question: "What has OIG found at the Columbia VA?", which matches three facilities: South Carolina (544), Missouri (589A4), and Washington, DC (688). The scripted user always chooses Missouri. Script: [`eval/elicitation/ab_run.py`](../../elicitation/ab_run.py). Raw runs, with every call and answer: [`runs-before-after.json`](runs-before-after.json), [`runs-no_form.json`](runs-no_form.json).*

## Arms

| Arm | Server | Client | How the user chooses |
|---|---|---|---|
| No form | Current (a408cf3) | Cannot show forms, like most hosts today | The server returns the matches and a next step; the model asks in chat; the user answers "The one in Missouri." |
| Form, before #114 | f133d93 | Shows the server's form | In the form. The result does not say the user chose |
| Form, after #114 | Current (a408cf3) | Shows the server's form | In the form. The result says the user chose and to answer for that facility only |

## Results (medians of five runs; every run in an arm gave the same counts)

| | Before elicitation: Claude asks in chat | After elicitation: the server's pick-list | Pick-list without the "user chose" note (before #114) |
|---|---|---|---|
| Calls to the server | 2 | 1 | 1 |
| Model requests | 4 | 2 | 2 |
| User turns | 2 | 1 | 1 |
| Tokens processed | 47,607 | 29,046 | 28,733 |
| Tool output read (characters) | 29,859 | 28,112 | 27,879 |
| Seconds, excluding the user's reply | 27.9 | 24.9 | 24.0 |
| Opened only the facility chosen | 5 of 5 | 5 of 5 | 5 of 5 |
| Answer pointed the user to another facility | 0 of 5 | 0 of 5 | 5 of 5 |
| Answer said the user chose this facility | n/a | 5 of 5 | 0 of 5 |

## What it shows

**The form halves the work of an ambiguous name.** Against the fallback every host can use, the form took one call instead of two, two model requests instead of four, one user turn instead of two, and 39 percent fewer tokens (29,046 against 47,607), for the same correct answer. Each request avoided re-reads the whole conversation, so the saving grows with the host's context: in Claude Code, whose own context is far larger than this harness's, a single take processed 171,280 tokens. The fallback also worked: with no form, the model asked in all five runs and never chose for the user.

**The form also takes the model out of the choice.** With no form, the user's answer passes through the model, which must turn "the one in Missouri" into a station number. With the form, the choice goes from the user to the server unchanged, and the server accepts only a station that matched.

**The choice notice (#114) changed the answer, not the cost.** Before it, all five answers told the user about the South Carolina facility, as if the server had guessed ("There's also a VA in Columbia, South Carolina... if you meant that one"). After it, all five said the user had picked this facility from the three and covered only it. The cost did not move. In Claude Code the missing notice was more expensive: two takes made three and four calls to the server, one looked up South Carolina and answered for both, and one asked the user again. This harness, without Claude Code's context, did not reproduce those extra calls.

## Limits

Five runs per arm, one question, one model, and one choice. The counts were identical within each arm, so the direction is firm; the token figures would differ with another question or host. The scripted user replies instantly, so the no-form time leaves out a person reading the list and typing an answer.
