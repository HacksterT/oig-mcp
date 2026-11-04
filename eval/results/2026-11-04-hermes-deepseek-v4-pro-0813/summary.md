# External run: DeepSeek V4 Pro 0813 through Hermes Agent

18 of the gold questions, judged by `claude-opus-5-5`. Tool use is as the agent reported it. The answers were written into an artifact in a format the operator set, unlike the isolated harness runs.

| Measure | Result |
|---|---|
| Questions passing every check | 11 of 18 |
| Exact facts present | 11 of 11 |
| Agrees with the gold reference | 18 of 18 |
| Tool selection, as reported | 14 of 14 |
| Caveats and behaviors | 10 of 13 |
| Every cited report number and link exists | 17 of 18 |
| Report number and link given where required | 0 of 6 |
| Data date stated where required | 4 of 4 |

## What failed

- **facility-el-paso-oldest**: no report number and link together
- **report-el-paso-2026**: no report number and link together
- **cluster-top-hfi**: caveat: The answer states El Paso's absence and the 21-report count definitively, without noting that automated grouping could miss related findings or make the count a lower bound.
- **search-plain-language**: no report number and link together
- **search-peer-actions**: no report number and link together
- **brief-el-paso**: caveat: It calls test-result workflows the 'single highest-probability' item El Paso might not see coming, which turns a peer finding into a likelihood prediction for El Paso.; caveat: Peer findings are ordered by frequency, but the answer makes its own risk rankings, calling items 3 and 4 'your exposure' and the expired-mask item 'the one to watch'.; unknown: ['26-00254-277']; no report number and link together
- **facility-clean-inspection**: no report number and link together
