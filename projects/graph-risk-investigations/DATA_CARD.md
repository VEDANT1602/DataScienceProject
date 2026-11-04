# Original synthetic customer-device transaction stream

## What one row means

One row is one fictional transaction, with a customer, device, amount, channel, country-change indicator, event timestamp, eventual binary outcome and separate label-availability timestamp. All IDs, outcomes and interactions are generated locally; no employer, client or real customer data is included.

Default seed: **41**. The fixed default stream contains 9,000 events across three chronological cohorts: 4,500 training events on days `[0,30)`, 1,800 validation events on `[35,45)` and 2,700 test events on `[50,70)`. Every cohort has a separate customer/device namespace. Labels arrive one to four days after the event.

## Mechanism and limitations

The generator makes 60 of each cohort's 600 possible customers latent coordinated accounts. They reuse a small pool of devices. Other customers normally share household devices, while some use benign public terminals. Amount and country changes carry weaker label signal. From day 60, coordinated accounts spread activity across more devices and their sampled positive-outcome probability changes.

This is a designed mechanism, not a sampled estimate of real fraud. Learning its signal demonstrates the implementation under these assumptions. It cannot establish production accuracy, prevalence, fairness, loss reduction or customer impact. Ring membership and the mechanism segment are excluded from features; the segment exists only for a declared test-slice audit. Exported customer and device IDs are opaque deterministic aliases, so analyst cards do not announce the latent mechanism in identifier text. This formatting is not a privacy or cryptographic security claim; the fictional generator is public.

## Availability contract

Graph context is computed from prior events in `[t-7days,t)`. Same-timestamp events are scored as a batch before their edges are inserted. Outcome labels and label availability never enter graph features. Exact retries are deduplicated; conflicting retries are rejected.

The replay assumes each event is observable at its timestamp. It has no arrival-time column or live late-event correction. Sorting an external event stream would not, by itself, establish online availability.

Training labels are mature at day 35. Validation labels are available by day 50; the final estimator refits on train and validation before freezing at day 50. The test audit uses outcomes available by day 75. The frozen estimator is not retuned after inspecting test results.

## Files and rights

Every experiment writes its own `data/transactions.csv.gz` and `data/manifest.json` beneath the selected output directory. The gzip header uses `mtime=0`; the manifest records compressed and decompressed SHA-256 hashes. Use the manifest alongside that report, rather than treating the default seed's package as data from a custom run.

The generated data is original and distributed under this project's MIT license. `graph_risk/data.py` is the numerical source of its mechanism. The stored generator seed and source hashes identify a run; no private assessment prompt is bundled.

## Metric interpretation

Average precision summarizes the scored held-out binary outcomes. Precision at capacity uses reviewed events as its denominator; recall uses all positive synthetic outcomes in that evaluated slice. Daily capacity is floored independently, so the actual reviewed fraction can be below 5%. Undefined AP, recall or precision remains N/A rather than being invented as zero.

The confidence interval resamples days of fixed predictions. It does not fully capture cross-day customer/ring dependence, alternate generators, training randomness, or a real-world target population. Analyst evidence cards omit outcome labels and are context summaries, not causal explanations or calibrated probabilities.
