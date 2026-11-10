# Selected work by experience

Six work samples, three professional conversations. I selected two examples for each area so a reader can inspect the decisions behind the work without opening the entire catalog.

These are **independent public implementations created in November 2026**, grouped by relevance to my LinkedIn experience. They contain no employer or customer code or data. The grouping does not place the experiments inside past employment, establish a deployment, or validate the historical business metrics on my profile. Each repository keeps its actual results and limitations visible.

## Ace: recommendations and fulfillment

The shared question is how a prediction becomes a useful product decision: which items to rank, which requests the model can cover, and which orders a feasible plan can serve.

| Selected work | My approach and recorded result | What it demonstrates |
| --- | --- | --- |
| [Temporal Recommendations](../projects/temporal-recommendations/) | I trained a PyTorch BPR ranker, split interactions by time, and compared the full eligible catalog with popularity. On the same 51 test users, NDCG@10 was **0.1636 versus 0.1377**. The paired interval includes zero; the coverage audit led to an explicit cold-start fallback. | Recommendation training, temporal evaluation, ranking metrics and a release decision that accounts for uncertainty and coverage. This is MovieLens research, not Gaana engagement evidence. |
| [Grocery Batch Planner](https://github.com/VEDANT1602/grocery-batch-planner) | I connected XGBoost duration estimates to OR-Tools CP-SAT, then independently verified assignments and a fallback. Across **600 fictional orders**, buffered optimization served **284 on time versus 275** for buffered greedy. Removing the buffer served 302 on time but made 13 late. | Fulfillment modeling, constraints, verification and an explicit volume/lateness tradeoff. This is new independent planning work, not an assertion that Ace operated this grocery system. |

**Secondary planning sample:** [Retail Demand Backtest](https://github.com/VEDANT1602/retail-demand-backtest) tests past-only features and a frozen store/SKU forecast comparison. It is an additional reading choice, rather than a third prominent LinkedIn work sample for this group. Its synthetic WAPE is **0.2239 versus 0.3999** for seasonal naive on 4,800 test rows, not a retailer's replenishment savings.

## CSAA: fraud and review signals

The shared question is what earns a place in a limited review workflow. I compare additional model complexity and selected thresholds with controls, keeping weak outcomes and unsupported labels in view.

| Selected work | My approach and recorded result | What it demonstrates |
| --- | --- | --- |
| [Hybrid Fraud GNN](https://github.com/VEDANT1602/hybrid-fraud-gnn) | I froze prior graph context and trained an inductive PyTorch encoder with CPU XGBoost controls on disjoint synthetic cohorts. At the same **80 reviews**, engineered graph statistics found **19 positives**, while the trained hybrid found **10**. I retained the stronger simple control. | Graph learning, leakage controls, fair model comparison and review-capacity evaluation. The generator is not a CSAA fraud benchmark. |
| [Claims Multilabel Signals](https://github.com/VEDANT1602/claims-multilabel-signals) | I fitted four logistic heads on fictional operational signals, selected thresholds on validation families, and withheld the rare label from the action comparison. On **800 held-out records**, macro F1 for the three supported labels was **0.6075 versus 0.5830** with fixed thresholds. One label regressed, and a declared shifted slice had lower AP. | Multilabel learning, support gates, family-disjoint evaluation and diagnostic reporting. It does not measure real claims decisions or insurer impact. |

## Independent work: inference and training systems

The shared question is whether a result can survive inspection and recovery. I separate measured hardware arithmetic from integration guides, and saved weights from a complete resumable training state.

| Selected work | My approach and recorded result | What it demonstrates |
| --- | --- | --- |
| [Inference Systems Lab](../projects/inference-systems-lab/) | I built streaming contracts, quality gates, fallback accounting and KV-cache checks. A separate free **Tesla T4 float16** run measured **25.626 ms** full recomputation versus **20.790 ms** KV reuse for tiny attention, with maximum difference **6.10e-05**. | Inference contracts, NVIDIA CUDA arithmetic and reproducible teaching material. The small untrained layer is not an LLM serving benchmark; vLLM serving, Nebius and Nsight measurements remain unexecuted. |
| [Checkpoint Integrity Lab](https://github.com/VEDANT1602/checkpoint-integrity-lab) | I captured model, Adam and CPU RNG state, rejected corrupt or incomplete newer snapshots, and resumed a small PyTorch network. Full-state recovery matched continuous training exactly in the recorded same-environment run; weights-only restoration diverged by **0.405736** in maximum parameter difference. | CPU training-state integrity, checkpoint selection and recovery parity. It does not establish GPU, distributed, Ray/FSDP or power-loss recovery. |

## Earlier work stays traceable

The original projects remain available separately: [FormVision](https://github.com/VEDANT1602/FormVision), [LLM-Powered Knowledge Base](https://github.com/VEDANT1602/LLM-Powered-Knowledge-Base), [Cryptocurrency Sentiment Analysis](https://github.com/VEDANT1602/Cryptocurrency-Sentiment-Analysis-System), [Heart Disease Prediction](https://github.com/VEDANT1602/Heart-Disease-Prediction-System), and [Car Price Prediction](https://github.com/VEDANT1602/Sales-Prediction-of-Cars-using-ML). Their original commits, files and scope are preserved; migration did not newly execute or validate them.

The car-price artifact is a co-authored ASU report by **Divyesh Rathod, Meet Shah and Vedant Thaker**. It is not reassigned to Ace or CSAA. The [earlier-work directory](repository-directory.md#earlier-projects-visible-separately-on-my-account) and [archive manifest](../legacy/migration-manifest.json) retain the credits and source history. The recommendation and inference labs above are earlier public work in this portfolio, now selected alongside newer experiments; their original publication and measurement scope stay intact.

For the complete catalog, use the [repository directory](repository-directory.md). For the boundary between these implementations and historical profile claims, use the [LinkedIn evidence map](linkedin-evidence-map.md).
