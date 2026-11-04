# Vedant Thaker | Applied AI and Decision Systems

I build around the decision a system needs to support: what evidence is available, what can go wrong, and what would make the next action defensible.

This portfolio turns that approach into runnable engineering work. Each project starts with a common workflow, exposes a specific failure mode, implements an alternative, and records the result of an actual experiment. The reports explain the reasoning; the code and run artifacts let you challenge it.

## Start with a problem

| Project | Decision | What to inspect |
| --- | --- | --- |
| [Evidence Gate](projects/evidence-gate/) | When should a document assistant answer, and when should it abstain? | Retrieval, evidence authority, validity windows, tenant boundaries, evaluation and a local API |
| [Point-in-time Risk](projects/point-in-time-risk/) | Which events deserve a limited review budget using only information available at scoring time? | Event replay, delayed labels, temporal features, model comparison, restart behavior and drift |
| [Temporal Recommendations](projects/temporal-recommendations/) | Does a learned ranker improve future-item retrieval over a simple popularity baseline? | PyTorch training, chronological evaluation, full-catalog ranking, coverage and cold-start limits |

These are independent portfolio implementations created in November 2026. They demonstrate engineering methods relevant to my professional interests; they do not reproduce employer or customer systems, verify historical workplace metrics, or imply customer deployment.

## What the executed experiments found

| Experiment | Observed result | Decision it supports |
| --- | --- | --- |
| Evidence contract | 24/24 correct contract decisions versus 5/24 for relevance-only retrieval on the fixed, author-written 24-case stress fixture | Metadata, ambiguity and abstention belong in the answer contract; this is a regression result, not a customer-accuracy estimate |
| Point-in-time review queue | 23 positive outcomes reviewed versus 21 at the same 142-review budget across 3,045 synthetic holdout events | The observed gain is modest, uncertainty includes no AP improvement, and shifted-period queues tie; keep testing before preferring the candidate |
| Recommendation coverage | The cold-start fallback system can score 8,291 of 8,471 held-out positive targets, compared with 869 in the warm-only model comparison | A coverage audit changes the system design; the measured NDCG difference still does not establish model superiority |

Full denominators, uncertainty, raw evaluation outputs and limitations are in the linked case studies. These results were measured on the included fictional data or the declared public-data protocol.

## Read the story, then reproduce the result

The project READMEs give setup and entry points. The case studies follow a common sequence:

1. Introduce the topic and the narrower decision.
2. Explain the usual approach and its failure modes.
3. Show the evidence that motivated a different design.
4. Compare the implementation with a stated baseline.
5. Report measured outcomes, uncertainty, tradeoffs and the next decision.

No paid API is required for the checked-in experiments. Evidence Gate and Risk use original fictional/synthetic data. Recommendations uses MovieLens under its research terms; its download script retrieves the data from GroupLens rather than redistributing it here.

## Run all three

Use Python 3.11 in a virtual environment. The root requirements record the tested dependency versions; each project also has a narrower standalone setup.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install torch==2.9.1 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements.txt
python scripts/verify.py
python scripts/reproduce.py
```

The last command reproduces the two fictional-data experiments and a tiny original recommendation fixture. Fresh outputs go to ignored `runs/reproduction/`; the committed results stay available for comparison. To reproduce the real MovieLens run, first read the [data terms](projects/temporal-recommendations/DATA_CARD.md), then run `python scripts/reproduce.py --include-public-data`.

[The recorded verification](reports/verification.json) identifies the executed tests and environment. The GitHub workflow runs contract tests; it does not claim to rerun the full public-data benchmark.

## How I approach the work

[My engineering method](docs/engineering-method.md) explains the framing and evidence standard. [The project-to-skills map](docs/portfolio-map.md) shows which parts of the implementation demonstrate applied AI, ML systems and customer-facing engineering skills. [Provenance and attribution](docs/provenance.md) separates original implementation, conceptual references and dataset terms.

The original [Netflix notebook](Netflix_Project-8.ipynb) remains available as earlier work. The three projects above are the current starting point.

**Author:** [Vedant Thaker / VEDANT1602](https://github.com/VEDANT1602) · [LinkedIn](https://www.linkedin.com/in/vedant-thaker/)
