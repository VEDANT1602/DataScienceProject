# Vedant Thaker: repository directory

The [Engineering Portfolio](engineering-portfolio.md) explains the design decisions and recorded results across recommendation and fulfillment, fraud and claims review, and inference and training systems.

The portfolio has focused repositories as well as the original collection. New work has its own problem statement, source, data contract and measured result. Earlier projects retain their original history and credits.

## November 9: twenty-two new repositories

The [new case-study directory](new-projects-2026-11-09.md) records all 22 implemented projects, their engineering decisions and tests. Thirteen separate repositories are published; nine remain prepared locally. It contains ten original redesigns inspired by AI Project Gallery, ten by Machine-Learning-Projects, and two additional projects informed by the 500-project index. The [source map](project-source-map.json) pins references and explains the conceptual-only reuse boundary. The projects span fulfillment, risk, analytics, applied AI, vision and ML infrastructure.

## Direct repositories from the original collection

| Repository | Engineering focus |
| --- | --- |
| [Temporal Recommendations](https://github.com/VEDANT1602/temporal-recommendations) | PyTorch ranking, chronological full-catalog evaluation and cold-start coverage. |
| [Inference Systems Lab](https://github.com/VEDANT1602/inference-systems-lab) | Streaming contracts, quality gates, KV-cache checks and the recorded small free-T4 attention experiment. |
| [Evidence Gate](https://github.com/VEDANT1602/evidence-gate) | Evidence-aware retrieval with authorization, validity, citation and abstention contracts. |

These are standalone forms of existing public implementations in the six-project collection. Their original project history, code, data and recorded results are preserved. The implementation counts include each project once; the collection remains available at its original links.

## Fulfillment and agent systems

| Repository | Engineering question | Evidence boundary |
| --- | --- | --- |
| [Grocery Batch Planner](https://github.com/VEDANT1602/grocery-batch-planner) | How should duration predictions feed a constrained assignment decision? | Actual XGBoost and OR-Tools CP-SAT on original synthetic orders. Store, capacity and predicted-deadline constraints, independent feasibility verification, bounded search and checked fallback. Buffering trades accepted volume for fewer late assigned orders. |
| [Fulfillment Policy Lab](https://github.com/VEDANT1602/fulfillment-policy-lab) | Do logged offers support the policy we want to test? | Known synthetic randomization, support/ESS gates, group cross-fitting, frozen policy selection, IPS/DR and cluster intervals. The selected policy misses the simulator-best candidate; unsupported policies receive no estimate. |
| [Agent Replay Lab](https://github.com/VEDANT1602/agent-replay-lab) | What survives a stopped worker and a missed acknowledgement? | Original SQLite DAG runner with leases/fencing, synthetic attempt reservations, transactional outbox and deduplicating local receiver. Five injected restart-boundary simulations; no live model or exactly-once external API claim. |
| [Decision Memory Lab](https://github.com/VEDANT1602/decision-memory-lab) | Which facts must survive a bounded agent handoff? | Original revision ledger, source digests, tenant checks, expiry/conflict refusal and whole-JSON UTF-8 byte budgeting. Fourteen authored contracts; no LLM answer-quality or provider token-savings claim. |

The agent projects take conceptual direction from [ECC](https://github.com/affaan-m/ECC), with pinned source credits in their own provenance documents. The fulfillment topics align with the methods requested in [Instacart's Senior Machine Learning Engineer, Fulfillment posting](https://www.instacart.careers/job?gh_jid=8240305). All four are new independent experiments; they contain no employer data or reconstructed workplace results.

## Fraud, prediction and search

| Repository | Engineering question | Evidence boundary |
| --- | --- | --- |
| [Hybrid Fraud GNN](https://github.com/VEDANT1602/hybrid-fraud-gnn) | Does a trained inductive graph encoder add value beyond useful XGBoost controls? | Actual PyTorch/CPU XGBoost, mature labels and disjoint synthetic cohorts. Engineered graph statistics beat the trained encoder in the recorded run. |
| [Dispatch ETA Lab](https://github.com/VEDANT1602/dispatch-eta-lab) | Does a more accurate ETA produce a better delivery promise under shift? | Actual CPU XGBoost, past-only conformal calibration, raw predictions and a declared synthetic disruption. Interval coverage and promise-policy loss are separate from point error. |
| [Tree Search Ranker](https://github.com/VEDANT1602/tree-search-ranker) | Can trees combine retrieval evidence, authority and query intent without weakening access boundaries? | Actual XGBRanker with scoped BM25 and TF-IDF/SVD features. Labels are authored fixture rules; no LLM, pretrained encoder or customer-quality claim. |

These projects take conceptual direction from [Andres Vourakis's discussion of production tree models](https://www.linkedin.com/posts/andresvourakis_xgboost-and-similar-tree-based-models-are-share-7523776256539029505-auas/). Their READMEs credit primary technical sources. Company code, datasets and reported improvements were not copied.

## Earlier projects, visible separately on my account

| Repository | Preserved scope |
| --- | --- |
| [FormVision](https://github.com/VEDANT1602/FormVision) | Original OpenCV/MediaPipe exercise notebooks, checkpoints and demonstration videos. |
| [LLM-Powered Knowledge Base](https://github.com/VEDANT1602/LLM-Powered-Knowledge-Base) | Original small sentence-embedding/cosine-retrieval prototype. |
| [Cryptocurrency Sentiment Analysis](https://github.com/VEDANT1602/Cryptocurrency-Sentiment-Analysis-System) | Original DistilBERT learning prototype using synthetic statements. |
| [Heart Disease Prediction](https://github.com/VEDANT1602/Heart-Disease-Prediction-System) | Original multimodal CNN/XGBoost pipeline; expected training data is absent and no clinical validation is claimed. |
| [Car Price Prediction](https://github.com/VEDANT1602/Sales-Prediction-of-Cars-using-ML) | Original co-authored ASU report. Divyesh Rathod, Meet Shah and Vedant Thaker retain their credits; runnable source/data is not bundled in that repository. |

Each restored `main` branch points to the same original source commit as the corresponding Vedant160297 repository. The [archive manifest](../legacy/migration-manifest.json) records those commits and all 35 file hashes. The existing [archive collection](../legacy/) remains as an additional preserved snapshot.

## The original six-project collection

[DataScienceProject](https://github.com/VEDANT1602/DataScienceProject) remains the home of Evidence Gate, Approval Workflow Lab, Point-in-time Risk, Graph Risk Investigations, Temporal Recommendations and Inference Systems Lab. The [portfolio map](portfolio-map.md) explains their measured outcomes and limits; the [LinkedIn evidence map](linkedin-evidence-map.md) distinguishes public implementations from historical workplace results.

All newly measured experiments are independent public work. They demonstrate current methods, not reconstructed private deployments, employer scale, customer adoption or historical business savings.
