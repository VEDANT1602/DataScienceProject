# Point-in-time Risk

**A fraud-review experiment where the clock, replay behavior and review capacity are part of the model contract.**

This is new independent portfolio work by Vedant Thaker. It demonstrates event-time feature engineering and evaluation discipline using **original synthetic transactions**. It does not reproduce an employer/client system or claim real fraud reduction.

Start with the [executed case study](artifacts/REPORT.md), then inspect the [raw measured metrics](artifacts/metrics.json) and [holdout predictions](artifacts/test_predictions.csv).

## Run it

Python 3.11 is the tested runtime. From this directory:

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m risklab demo --out artifacts
```

The demo generates 12,000 fictional events, records point-in-time features in SQLite, handles exact retries and late examples, runs a chronological model comparison, and writes the narrative and charts from the same `metrics.json` source. It needs no credentials, external dataset, paid API or GPU. The command prints the output location and test metrics.

The CLI defaults `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS` and `MKL_NUM_THREADS` to `1` before importing numerical libraries. These defaults affect only the CLI process and avoid oversubscription for this small CPU experiment; any explicitly supplied environment values are respected. The committed run used these one-thread limits.

For the exact dependency versions used in the committed run, install `requirements-lock.txt` instead. The [packaged original synthetic dataset](data/transactions.csv.gz) is included, with its decompressed SHA256 in the data card. Inspect it without rerunning model training:

```bash
python -m risklab unpack-data --out data/unpacked-transactions.csv
```

```bash
# A fresh experiment, not a manual change to the published metrics:
python -m risklab demo --out runs/seed-23 --seed 23
# Regenerate the report and SVGs from existing measured results:
python -m risklab report --out artifacts
```

## What is implemented

- SQLite event ledger with content-hashed idempotence, atomic event/feature/checkpoint writes, restart recovery and explicit late-event quarantine.
- Point-in-time customer/device features over `[t-window, t)`; no outcome fields in the serving schema.
- Separate event time and label availability; chronological selection, maturity filtering, deployment embargo and untouched final holdout.
- Static logistic regression versus validation-selected temporal gradient boosting.
- An explicitly exploratory static-feature boosting ablation checks the model-class alternative without retuning the candidate.
- A deliberately invalid future-marker diagnostic, isolated from model selection and eligible serving features.
- Exact daily review-capacity accounting, row-level prediction evidence, declared synthetic drift segments and paired day-block bootstrap intervals.
- Tests for failure behavior rather than merely checking that a function returns a value.

## Explore the code

| File | Responsibility |
|---|---|
| [risklab/store.py](risklab/store.py) | Decision-time schema, feature windows, transaction semantics and replay |
| [risklab/data.py](risklab/data.py) | Original data mechanism, outcome delays and split boundaries |
| [risklab/experiment.py](risklab/experiment.py) | Baselines, validation selection and capacity metrics |
| [risklab/report.py](risklab/report.py) | Narrative and charts generated from measured JSON |
| [tests/test_contracts.py](tests/test_contracts.py) | Leakage, retry, rollback, restart, late-data and evaluation contracts |
| [data/DATA_CARD.md](data/DATA_CARD.md) | Grain, fields, license, synthetic mechanism and limitations |

## What this does not establish

The labels were sampled from a published synthetic rule. A model that learns that mechanism has not demonstrated production fraud accuracy. The tiny single-writer SQLite service is not a distributed feature platform. Review metrics rank a daily offline queue and are not a production blocking threshold. No calibration, fairness validation, business costs, customer harm assessment or real-world adoption is claimed.

The late policy favors stable historical decisions over use of out-of-order data. A real pilot would need representative data, observed label delays, an allowed-lateness contract and operational review costs before any financial or deployment recommendation.

## Attribution

Conceptual inspiration: [Build Your Own X](https://github.com/codecrafters-io/build-your-own-x), especially its database and distributed-systems categories. This implementation, its synthetic data mechanism, evaluation and reports are original. No tutorial code or third-party benchmark results were copied. Dependency APIs: [Python sqlite3](https://docs.python.org/3/library/sqlite3.html), [scikit-learn](https://scikit-learn.org/stable/).

Code and original synthetic data are provided under the [MIT License](LICENSE).
