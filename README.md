# Vedant Thaker | Applied AI and Decision Systems

My first notebook in this collection explored the Netflix catalog in 2021. The newer work asks questions that come up when a model has to support a decision. One example is the [MovieLens recommender](https://github.com/VEDANT1602/temporal-recommendations): before comparing two rankings, it matters whether either model can score the user’s next item at all. [Original notebook commit](https://github.com/VEDANT1602/DataScienceProject/commit/a52fa4d2b60274a6d975cbbd10b75d89a8ebc8cf)

The [engineering portfolio](docs/engineering-portfolio.md) covers recommendations and fulfillment, fraud review, and inference. Use the [repository directory](docs/repository-directory.md) to find a standalone implementation. The [case-study index](docs/new-projects-2026-11-09.md) tracks the 13 published and nine locally prepared entries in the November collection.

## Research working papers

| Paper | Status | Research materials |
| --- | --- | --- |
| [Two-marker fixture yaw estimation](https://github.com/VEDANT1602/fixture-pose-correction/blob/main/manuscript.pdf) | Working paper | [Code and results](https://github.com/VEDANT1602/fixture-pose-correction/tree/main/study) · [Preparation record](https://github.com/VEDANT1602/fixture-pose-correction/blob/main/study/PREPARATION.md) |
| [Auxiliary texture prediction and delayed recall](https://github.com/VEDANT1602/delayed-cue-recall/blob/main/manuscript.pdf) | Working paper | [Code and results](https://github.com/VEDANT1602/delayed-cue-recall/tree/main/study) · [Preparation record](https://github.com/VEDANT1602/delayed-cue-recall/blob/main/study/PREPARATION.md) |
| [Reconstructing incomplete analysis records](https://github.com/VEDANT1602/materials-workflow-replay/blob/main/manuscript.pdf) | Working paper | [Code and results](https://github.com/VEDANT1602/materials-workflow-replay/tree/main/study) · [Preparation record](https://github.com/VEDANT1602/materials-workflow-replay/blob/main/study/PREPARATION.md) |
| [Caliper checks for extrusion-width measurement](https://github.com/VEDANT1602/bead-width-inspection/blob/main/manuscript.pdf) | Technical note | [Code and results](https://github.com/VEDANT1602/bead-width-inspection/tree/main/study) · [Preparation record](https://github.com/VEDANT1602/bead-width-inspection/blob/main/study/PREPARATION.md) |
| [Repeated stiffness solves in a cut spring network](https://github.com/VEDANT1602/lattice-fracture-calibration/blob/main/manuscript.pdf) | Technical note | [Code and results](https://github.com/VEDANT1602/lattice-fracture-calibration/tree/main/study) · [Preparation record](https://github.com/VEDANT1602/lattice-fracture-calibration/blob/main/study/PREPARATION.md) |
| [Shared uncertainty in dispatch decisions](https://github.com/VEDANT1602/verified-robot-dispatch/blob/main/manuscript.pdf) | Technical note | [Code and results](https://github.com/VEDANT1602/verified-robot-dispatch/tree/main/study) · [Preparation record](https://github.com/VEDANT1602/verified-robot-dispatch/blob/main/study/PREPARATION.md) |
| [Carbon accounting for one-hour HPC deferrals](https://github.com/VEDANT1602/carbon-aware-scheduling-replay/blob/main/manuscript.pdf) | Technical note | [Code and results](https://github.com/VEDANT1602/carbon-aware-scheduling-replay/tree/main/study) · [Preparation record](https://github.com/VEDANT1602/carbon-aware-scheduling-replay/blob/main/study/PREPARATION.md) |
| [Two low-field readings of a magnetic strip](https://github.com/VEDANT1602/magnetic-cantilever-clearance/blob/main/manuscript.pdf) | Technical note | [Code and results](https://github.com/VEDANT1602/magnetic-cantilever-clearance/tree/main/study) · [Preparation record](https://github.com/VEDANT1602/magnetic-cantilever-clearance/blob/main/study/PREPARATION.md) |
| [Timing a sixth elliptical-rim contact](https://github.com/VEDANT1602/aperture-contact-localization/blob/main/manuscript.pdf) | Technical note | [Code and results](https://github.com/VEDANT1602/aperture-contact-localization/tree/main/study) · [Preparation record](https://github.com/VEDANT1602/aperture-contact-localization/blob/main/study/PREPARATION.md) |
| [Foothold clearance and route coverage](https://github.com/VEDANT1602/foothold-margin-planning/blob/main/manuscript.pdf) | Technical note | [Code and results](https://github.com/VEDANT1602/foothold-margin-planning/tree/main/study) · [Preparation record](https://github.com/VEDANT1602/foothold-margin-planning/blob/main/study/PREPARATION.md) |

## Earlier projects revisited on November 19

For FormVision, the February 2025 commit already contains the pose notebooks and videos. The November update points from the rep-counting rules to the annotated clip. [Original implementation](https://github.com/VEDANT1602/FormVision/commit/6cca5261bcc026f2716690c66a53c3795b59cc8b) · [Documentation update](https://github.com/VEDANT1602/FormVision/commit/1ae9e609ea4f5bf83911884018f87f0534ad02f2)

The spoken-digit classifier also dates to 2025. The November revision repaired the audio entry points and added a fresh evaluation on the supplied recording split. [August source](https://github.com/VEDANT1602/spoken-digit-classifier/commit/f232c8b94efc8985df87815f4051f8097dd62ac8) · [November revision and run record](https://github.com/VEDANT1602/spoken-digit-classifier/commit/7731e9c853431055c570c727b9308d4ab76c1462)

## Start with a problem

| Project | Engineering question | Where to look |
| --- | --- | --- |
| [Evidence Gate](https://github.com/VEDANT1602/evidence-gate) | When should a document assistant answer, and when should it abstain? | Retrieval, evidence authority, validity windows, tenant boundaries, evaluation and a local API |
| [Point-in-time Risk](projects/point-in-time-risk/) | Which events deserve a limited review budget using only information available at scoring time? | Event replay, delayed labels, temporal features, model comparison, restart behavior and drift |
| [Temporal Recommendations](https://github.com/VEDANT1602/temporal-recommendations) | Does a learned ranker improve future-item retrieval over a simple popularity baseline? | PyTorch training, chronological evaluation, full-catalog ranking, coverage and cold-start limits |
| [Graph Risk Investigations](projects/graph-risk-investigations/) | Do prior entity connections improve a fixed-capacity fraud review queue? | Leakage controls, graph features, entity-disjoint evaluation, drift and analyst evidence cards |
| [Approval Workflow Lab](projects/approval-workflow-lab/) | How can a tool execute exactly the transaction a separate reviewer approved? | Signed approvals, tenant-isolated SQL, atomic audit, replay protection and concurrency |
| [Inference Systems Lab](https://github.com/VEDANT1602/inference-systems-lab) | Can a serving comparison survive malformed answers, fallback and missing measurements? | Streaming vLLM/Nebius adapters, quality gates, KV-cache arithmetic, NVIDIA runbook and a free GPU notebook |

These are independent portfolio implementations created in November 2026. They demonstrate engineering methods relevant to my professional interests; they do not reproduce employer or customer systems, verify historical workplace metrics, or imply customer deployment.

## What the executed experiments found

| Experiment | Observed result | Decision it supports |
| --- | --- | --- |
| Evidence contract | 24/24 correct contract decisions versus 5/24 for relevance-only retrieval on the fixed, author-written 24-case stress fixture | Metadata, ambiguity and abstention belong in the answer contract; this is a regression result, not a customer-accuracy estimate |
| Point-in-time review queue | 23 positive outcomes reviewed versus 21 at the same 142-review budget across 3,045 synthetic holdout events | The observed gain is modest, uncertainty includes no AP improvement, and shifted-period queues tie; keep testing before preferring the candidate |
| Recommendation coverage | The cold-start fallback system can score 8,291 of 8,471 held-out positive targets, compared with 869 in the warm-only model comparison | A coverage audit changes the system design; the measured NDCG difference still does not establish model superiority |
| Graph review queue | 18 positive outcomes reviewed versus 9 for static features at the same 126-review budget across 2,700 synthetic test events | Prior graph context helps on this generator; only one of the nine additional outcomes is after the distribution shift |
| Transaction approval | 40/40 authored evaluation contracts and 8/8 development examples; eight concurrent retries apply one mutation | Bind approval to the exact transaction and commit mutation, receipt and audit together; this is protocol validation, not LLM accuracy |
| Attention arithmetic | Tiny CPU float32 attention: 12.064 ms full recomputation versus 4.107 ms KV reuse; maximum numerical difference 5.22e-08 | Reuse is correct for the checked tensors; this toy CPU result does not measure vLLM, NVIDIA GPU speed or provider savings |
| Real CUDA arithmetic | Free Colab Tesla T4, float16: 25.626 ms full recomputation versus 20.790 ms KV reuse over seven trials; maximum difference 6.10e-05 | The separate [hardware-backed check](projects/inference-systems-lab/results/colab-t4/) passes the declared tolerance for tiny attention; it is not an LLM serving benchmark or a CPU/GPU comparison |

Full denominators, uncertainty, raw evaluation outputs and limitations are in the linked case studies. These results were measured on the included fictional data or the declared public-data protocol.

## What a second run should test

For graph-based fraud review, only one of the nine additional positive reviews came after the simulated shift. Another shift window would test whether that gain holds. For recommendations, I’d report ranking quality and the count of eligible held-out ratings together from the first run. A score on warm users alone leaves out most of the positive targets in this split.

No paid API is required for the checked-in experiments. Five projects use original fictional/synthetic fixtures or local tensor arithmetic. Recommendations uses MovieLens under its research terms; its download script retrieves the data from GroupLens rather than redistributing it here.

## Run all six

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

The last command reproduces five local experiments and a tiny original recommendation fixture. Fresh outputs go to ignored `runs/reproduction/`; the committed results stay available for comparison. To reproduce the real MovieLens run, first read the [data terms](projects/temporal-recommendations/DATA_CARD.md), then run `python scripts/reproduce.py --include-public-data`.

[The recorded verification](reports/verification.json) identifies the executed tests and environment. The GitHub workflow runs contract tests; it does not claim to rerun the full public-data benchmark.

## How I approach the work

[My engineering method](docs/engineering-method.md) explains the framing and evidence standard. [The project-to-skills map](docs/portfolio-map.md) shows which parts of the implementation demonstrate applied AI, ML systems and customer-facing engineering skills. [The LinkedIn evidence map](docs/linkedin-evidence-map.md) connects public artifacts to professional methods and identifies which historical outcomes require their original records. [Provenance and attribution](docs/provenance.md) separates original implementation, conceptual references and dataset terms.

The 2021 [Netflix exploration notebook](Netflix_Project-8.ipynb) retains its original cell outputs. Its first data-loading cell points to a local CSV outside this repository. The saved actor search spells ‘Tom Cruize’, so its empty result is unreliable. Re-running that analysis requires the original CSV or a schema-compatible licensed copy. The six bundled projects above and the linked standalone repositories are the current starting points.

## GPU, vLLM, NVIDIA and Nebius

[Open the free Colab lab](https://colab.research.google.com/github/VEDANT1602/DataScienceProject/blob/master/projects/inference-systems-lab/notebooks/free_gpu_lab.ipynb) for the conditional NVIDIA CUDA experiment. It checks actual hardware and records the resolved code revision. Free GPU availability varies. The optional in-process vLLM cells are disabled until explicitly enabled; there are no tunnels, provider keys or paid resource allocations.

The [NVIDIA runbook](projects/inference-systems-lab/docs/gpu-runbook.md), [vLLM migration guide](projects/inference-systems-lab/docs/migrate-to-vllm.md), [Nebius migration guide](projects/inference-systems-lab/docs/migrate-to-nebius.md) and [20-minute workshop](projects/inference-systems-lab/docs/workshop-20-minutes.md) show implementation and teaching artifacts. The original Windows run has no CUDA device. A separate [free Colab T4 run](projects/inference-systems-lab/results/colab-t4/) now records actual CUDA attention correctness and raw timing trials. vLLM serving, Nebius and Nsight measurements remain unexecuted. The streaming adapter was exercised against a loopback fixture only.

**Author:** [Vedant Thaker / VEDANT1602](https://github.com/VEDANT1602) · [LinkedIn](https://www.linkedin.com/in/vedant-thaker/)

## Earlier projects from my other GitHub account

The [historical project collection](legacy/) preserves all five public repositories from [Vedant160297](https://github.com/Vedant160297): FormVision, the LLM knowledge-base prototype, cryptocurrency sentiment analysis, the heart-prediction prototype, and the co-authored car-prediction report. Original files, credits, source commits and limitations remain visible.

The migration manifest records 35 original files and their hashes. These snapshots retain their original scope; they are separate from the newly executed portfolio experiments above. See the [index and verification instructions](legacy/README.md) before trying to run an older notebook.

The five earlier projects are also published as individual repositories under **VEDANT1602**, with their original source commits unchanged. Open the [directory](docs/repository-directory.md#earlier-projects-visible-separately-on-my-account) or the [Repositories tab](https://github.com/VEDANT1602?tab=repositories) to find them directly.
