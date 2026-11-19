# Streaming measurements from the loopback fixture

The server returns known answers. This run checks whether the client records admission, first content, completion, task quality and retry costs consistently. Its timings belong to the fixture and client on this host.

## Which requests finished within the serving contract?

The batch scheduled 12 requests at concurrency 2. Across 12 attempts, 12 requests completed the stream, 12 returned an accepted schema and label, and 12 met the post-admission latency limits as well.

| Batch observation | Value |
| --- | ---: |
| HTTP and stream completions | 12/12 |
| Correct responses | 12/12 |
| Responses meeting the SLO | 12/12 |
| First nonempty content, accepted answers, p50 / p95 | 6.306 / 8.565 ms |
| Post-admission end-to-end latency, all requests, p50 / p95 | 17.040 / 19.717 ms |

First content is measured when a nonempty chunk arrives. A chunk may contain several tokens, so inter-token latency is unknown. The all-request end-to-end denominator retains failed and rejected answers. The trace records client queue time separately, and a retry retains the failed attempt's time and known usage.

[Per-request and per-attempt traces](traces.jsonl)

## A separate tensor calculation

The recorded device is **Intel64 Family 6 Model 78 Stepping 3, GenuineIntel**, with dtype float32, width 64 and 4 attention heads. Both paths use a prefix of 64 positions and decode 24 positions. The cached path includes prefill.

The two implementations agree at the declared tolerance on these inputs. Maximum absolute difference was **5.2154064e-08**. After 2 warmups, 7 repetitions gave medians of **12.064 ms** for dense recomputation and **4.107 ms** with projected KV reuse.

The benchmark uses a single untrained attention layer. It times tensor operations and omits the scheduler, tokenizer and trained model needed for an end-to-end serving comparison.

## What goes into the cost estimate?

The entered input and output rates per million tokens are 1.000 and 2.000. The entered dedicated hourly rate is 1.000. Complete usage for all attempts: True.

The economic break-even under those inputs is **3.655 requests per second**. A missing rate or usage needed for the calculation leaves the estimate unavailable. A deployment would also have to sustain that rate at the same quality and tail-latency limits. The fixture's illustrative rates cannot establish a provider price or a capacity result.

## Evidence for a serving comparison

To test prefix caching, pair a fresh-process run with repeated-prefix requests and record cache state alongside both traces. A phase label alone cannot establish a reset or a hit. Keep the same workload, output limit and concurrency for both conditions.

- [Workload and data card](../data/DATA_CARD.md)
- [GPU and endpoint runbook](../docs/gpu-runbook.md)
- [Metric definitions](../docs/measurement-contract.md)
- [Separate archived T4 attention run](colab-t4/README.md)
- [Metrics and execution environment for this run](metrics.json)

Independent systems experiment by Vedant Thaker.
