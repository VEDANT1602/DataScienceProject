# Original synthetic transaction dataset

## Purpose and origin

This dataset was created specifically for this independent portfolio experiment by `risklab.data.generate`. It contains no real customer, payment, employer or client records. All IDs, amounts, timestamps and outcomes are fictional. Amounts use arbitrary currency units and should not be converted into business value.

The default seed is 19. The demo generates 12,000 events across a 90-day synthetic clock. A complete compressed CSV is included as `data/transactions.csv.gz`, packaged with gzip timestamp zero. The exact decompressed CSV hash and row count are recorded in `artifacts/metrics.json`. Re-running the generator with the same Python runtime and seed reproduces the rows. The data uses UTF-8 and LF line endings.

## Grain and fields

One row is one simulated transaction, before duplicate-delivery and deliberately late replay examples are injected. Duplicate deliveries do not create additional modeling rows. Outcomes are separate from the decision-time projection used by the feature store.

| Field | Meaning | Availability |
|---|---|---|
| event_id | Unique fictional transaction ID | At event |
| event_time | Integer seconds since synthetic day zero | At event |
| customer_id, device_id | Fictional entity identifiers | At event |
| amount | Positive arbitrary-unit transaction amount | At event |
| country_changed | Simulated binary country-change signal | At event |
| channel | `web` or `mobile` | At event |
| fraud | Bernoulli-sampled synthetic outcome, not adjudicated real fraud | `label_available_at` |
| label_available_at | Event time plus an integer delay of 2-7 days | Offline outcome ledger |
| future_dispute_marker | Noisy investigation outcome marker, deliberately unavailable at decision time | `dispute_marker_available_at` |
| dispute_marker_available_at | Same delayed investigation timestamp | Offline outcome ledger |
| segment | Whether generator uses the original or day-72 shifted mechanism | Diagnostic metadata only |

## Generation mechanism

Customer and device patterns include shared-device bursts and occasional new devices. The label probability is a logistic function of amount, country change, device novelty, previous device sharing and recent customer velocity, plus stochastic sampling. On day 72 the generator weakens the sharing coefficient and strengthens the country-change coefficient. These designed relationships are disclosed so a reader can challenge the experiment; they are not discovered properties of payment data.

The future dispute marker is sampled with 97% sensitivity and 0.8% false-positive probability relative to the synthetic label. It exists to demonstrate leakage. It is not a valid serving feature, even though its diagnostic classifier is evaluated in a separate column.

## Temporal split contract

- Selection training: transactions before day 45 with labels available by day 45.
- Validation: event days 45-59, outcomes available by day 67.
- Final training after model choice: transactions before day 60 with outcomes known by day 67.
- Embargo: event days 60-66 affect accepted online history but do not enter training or validation.
- Holdout: event days 67-89, scored by the frozen model and evaluated as of day 100.

Training customers may reappear in the holdout, matching a repeated-customer use case. This is not an unseen-customer generalization experiment. No test results select hyperparameters.

## Fitness and limits

Suitable for testing event-time windows, label maturity, replay contracts and reproducible evaluation machinery. Not suitable for estimating field accuracy, losses, financial savings, unfairness across real groups or deployment readiness. There are no demographic attributes. Their absence does not establish fairness.

## License

The generator and its original synthetic outputs are licensed under the project's MIT License. There are no third-party data redistribution requirements. `replay.sqlite` and the generated uncompressed transaction CSV are reproducible and excluded from Git by default; the committed gzip dataset, predictions and metrics support inspection without the database.

## Packaged-data integrity

Decompressed SHA256: `a887427d22298b09e35446a1e3c78877d5da493cca0718c00949ff472cf9049e`.

Compressed SHA256: `d12d39b3c8ebfee66594780cc31669134ca1d99e7cd1bac350efd49e4c89af76`.
