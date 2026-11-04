# External run: DeepSeek V4 Pro 0813 through Hermes Agent

17 of the gold questions, judged by `claude-opus-5-5`. Tool use is as the agent reported it. The answers came from one continuing session and were written into an artifact, unlike the isolated harness runs.

| Measure | Result |
|---|---|
| Questions passing every check | 10 of 17 |
| Exact facts present | 10 of 10 |
| Agrees with the gold reference | 17 of 17 |
| Tool selection, as reported | 13 of 13 |
| Caveats and behaviors | 11 of 12 |
| Every cited report number and link exists | 17 of 17 |
| Report number and link given where required | 0 of 5 |
| Data date stated where required | 2 of 4 |

## What failed

- **count-hfi-2026**: data date not stated
- **facility-el-paso-oldest**: no report number and link together
- **report-el-paso-2026**: no report number and link together
- **cluster-top-hfi**: caveat: The answer states El Paso's absence and the count of 21 without noting that grouping is automated, that the theme could appear in other groups, or that the count may be a lower bound.
- **search-plain-language**: no report number and link together; data date not stated
- **search-peer-actions**: no report number and link together
- **brief-el-paso**: no report number and link together
