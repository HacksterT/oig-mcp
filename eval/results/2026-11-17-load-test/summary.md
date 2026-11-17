# Load test, November 17, 2026

Run with [`deploy/load_test.py`](../../../deploy/load_test.py) from 14:22 to 14:29 UTC, against the hosted server through its public URL: Cloudflare Tunnel to the container on the Mac, which reaches the data API through Cloudflare Access. No model was involved: each simulated client, with its own token, repeated tool calls recorded in the November 17 Claude Sonnet 5.5 and Opus 5.5 runs (105 calls: dataset status 40, analysis 32, facility profile 15, search 7, clusters 5, inspection brief 4, report 2), pausing about one second between calls. Each stage ran for 60 seconds. Raw results: [`stages.json`](stages.json).

| Clients | Calls | Calls per second | Answered | Refused or failed | Median | 95th percentile | 99th percentile | Data API requests per second |
|---|---|---|---|---|---|---|---|---|
| 1 | 42 | 0.7 | 42 | 0 | 0.33 s | 0.54 s | 0.92 s | 2.0 |
| 5 | 214 | 3.4 | 214 | 0 | 0.35 s | 0.96 s | 2.2 s | 11.7 |
| 10 | 394 | 6.1 | 394 | 0 | 0.35 s | 2.3 s | 4.2 s | 20.1 |
| 20 | 586 | 9.6 | 586 | 0 | 0.75 s | 3.2 s | 4.9 s | 27.7 |
| 40 | 823 | 13.2 | 823 | 0 | 1.8 s | 4.1 s | 6.0 s | 37.5 |

**Every call was answered.** All 2,059 calls returned a result: no rate-limit refusals (each client had its own token), no "data API busy" or "search too slow" answers, no errors, and no reply with a credential, upstream address, or internal detail. The data API answered all 5,941 of the load clients' requests with status 200.

**It slows down, and does not fail.** Throughput kept rising to 40 clients, but less than in proportion, as each call waited longer. At 40 clients the median call took 1.8 seconds; the inspection brief, which makes up to 14 data API calls, had a median of 5.4 seconds and a slowest of 8.7.

**Where the time went.** Inside the data API, the median request took 7 to 13 milliseconds at every stage; searches, the slow part, took about 1.5 seconds under load. So the added time is ahead of the data API, not in it. The likely cause is the server's own limit of eight upstream requests in flight at once, which protects the data API's four search slots, so that quick calls queue behind searches. That limit is why the data API never had to turn a request away. CPU and memory were not measured during the run, so this is the likely cause, not a proven one.

**Limits of the test.** One run, on one Mac, with one data API. Sixty seconds per stage, and about one second between calls, which is faster than an agent that waits for a model between calls. The test went to 40 clients and was not run until something failed.

**What would help next.** A separate limit for searches would let quick calls pass searches waiting for a slot. It was not made: 40 agents calling at once is far beyond the expected use, and every call was answered.
