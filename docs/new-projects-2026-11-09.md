# Twenty-two original engineering case studies

These new independent portfolio projects follow the same method: narrow the decision, expose a failure mode, implement a different mechanism, compare actual outputs, and retain the limit. They were built in November 2026 for Vedant Thaker with AI implementation assistance.

The source map contains **10 distinct inspirations from AI Project Gallery, 10 from Machine-Learning-Projects, and two from the 500-project index**. Sources supplied ideas; code, fixtures, model artifacts and measured results are new. No source notebook, dataset, weights, screenshots or reported performance was copied.

**Publication status: 13 repositories published; 9 prepared locally.** Claims Multilabel Signals, Checkpoint Integrity Lab and Retail Demand Backtest were published on November 10, following GitHub's temporary creation limit on November 9. Prepared entries below are not live links; their reviewed code, data, models and results remain in the local source archive. Publication status does not change their measured local results. The [Engineering Portfolio](engineering-portfolio.md) explains the systems, design decisions and results across the main engineering domains.

The reviewed local run passes **214 tests across 22 repositories**. Test totals combine different contracts and are not an accuracy score. Every repository includes pinned CI, a reproducible run, input/result commitments and a data card. See the [machine-readable source map](project-source-map.json).

## AI Project Gallery: ten redesigned workflows

| Project | Decision to inspect | Tests | Publication |
|---|---|---:|---|
| [Article Change Ledger](https://github.com/VEDANT1602/article-change-ledger) | Can an ingestion job resume without losing or duplicating article revisions? | 10 | published |
| [Retail Metric Contracts](https://github.com/VEDANT1602/retail-metric-contracts) | Do the sales and fulfillment metrics agree once refunds, retries and cancellations are counted correctly? | 11 | published |
| [Fare Snapshot Audit](https://github.com/VEDANT1602/fare-snapshot-audit) | Can a fare model use only the information available at quote time and recognize when a quote is stale? | 10 | published |
| [Gesture Command Filter](https://github.com/VEDANT1602/gesture-command-filter) | When should a noisy hand-landmark stream produce exactly one UI command? | 10 | published |
| [Image Duplicate Audit](https://github.com/VEDANT1602/image-duplicate-audit) | Does an image evaluation remain independent when resized or slightly altered copies cross the split? | 10 | published |
| [Store Cohort Audit](https://github.com/VEDANT1602/store-cohort-audit) | Did a regional operational metric improve within comparable stores, or only because the store mix changed? | 10 | published |
| [API Documentation Contracts](https://github.com/VEDANT1602/api-doc-contracts) | Which public API documentation claims have become stale after a code change? | 11 | published |
| [Report Number Auditor](https://github.com/VEDANT1602/report-number-auditor) | Bind numerical report claims to artifact, population, denominator and unit. | 9 | published |
| [Snapshot Completeness Monitor](https://github.com/VEDANT1602/snapshot-completeness-monitor) | Emit membership changes only after a coherent complete snapshot is assembled. | 12 | published |
| [Field Visit Planner](https://github.com/VEDANT1602/field-visit-planner) | Choose a feasible multi-day customer-visit itinerary under time windows and daily budgets. | 10 | published |

## Machine-Learning-Projects: ten redesigned experiments

| Project | Decision to inspect | Tests | Publication |
|---|---|---:|---|
| [Retail Demand Backtest](https://github.com/VEDANT1602/retail-demand-backtest) | Which model should supply SKU/store replenishment inputs when promotions and missing history change? | 9 | published |
| Credit Calibration Lab | When should a calibrated score be withheld or recalibrated instead of turning a ranking result into an approval rule? | 8 | prepared; repository creation pending |
| Merchant Churn Cohorts | Does a model identify future merchant inactivity beyond tenure and cohort artifacts? | 9 | prepared; repository creation pending |
| Batch Quality Triage | Should an operations model predict a quality score or prioritize costly batch failures? | 8 | prepared; repository creation pending |
| Document Topic Routing | Which team should receive a technical document when it spans topics or resembles an unseen category? | 8 | prepared; repository creation pending |
| Reservation Dialog Contracts | Can a booking assistant collect missing fields and reserve capacity exactly once despite repeated messages and concurrent requests? | 10 | prepared; repository creation pending |
| Fulfillment Task State | Do sequence windows distinguish pick/pack/wait/move states without leakage from the same simulated worker session? | 8 | prepared; repository creation pending |
| Aisle Geometry Lab | Estimate a synthetic aisle direction only when two pixel-line fits have enough support. | 10 | prepared; repository creation pending |
| Occupancy Event Counter | Count anonymous directional crossings once despite pauses, short occlusion and duplicate frames. | 11 | prepared; repository creation pending |
| [Claims Multilabel Signals](https://github.com/VEDANT1602/claims-multilabel-signals) | Predict co-occurring fictional review reasons without hiding rare-label support behind one threshold. | 11 | published |

## 500-project index: two additional engineering questions

| Project | Decision to inspect | Tests | Publication |
|---|---|---:|---|
| Inventory Bellman Lab | Choose replenishment orders while tracking the two-period pipeline and finite horizon. | 9 | prepared; repository creation pending |
| [Checkpoint Integrity Lab](https://github.com/VEDANT1602/checkpoint-integrity-lab) | Resume the same training trajectory after rejecting newer incomplete or corrupt snapshots. | 10 | published |

## Engineering domains

| Domain | Implementations | Engineering focus |
|---|---|---|
| Fulfillment and operations research | Retail Demand Backtest, Inventory Bellman Lab, Field Visit Planner, Retail Metric Contracts | Demand boundaries, pipeline state, constrained planning, paired simulation and auditable SQL grain. |
| Risk and review systems | Credit Calibration Lab, Claims Multilabel Signals, Batch Quality Triage | Probability quality under shift, label-specific support and decision-cost tradeoffs. These are fictional advisory experiments, not eligibility decisions. |
| Product analytics and retention | Merchant Churn Cohorts, Store Cohort Audit | Mature follow-up, fixed-capacity review, population mix and standardization; association is not a causal intervention effect. |
| Applied AI and forward-deployed engineering | Document Topic Routing, Reservation Dialog Contracts, Article Change Ledger, Report Number Auditor, Snapshot Completeness Monitor, API Doc Contracts | Learned routing plus bounded workflow state, integrity, completeness, typed numerical evidence and contract drift. |
| Vision and robotics methods | Fulfillment Task State, Gesture Command Filter, Aisle Geometry Lab, Occupancy Event Counter, Image Duplicate Audit | Temporal features, hysteresis, geometric support, event tracking and grouped image evaluation on original synthetic fixtures. |
| ML infrastructure | Checkpoint Integrity Lab | Actual CPU model/optimizer/RNG recovery after integrity-qualified checkpoint selection. No distributed/GPU recovery claim. |

## Evidence limits

All inputs are original synthetic or authored fixtures. The projects demonstrate present methods and failure handling. They do not verify employer/client scale, historical business improvements, customer adoption, private pilots, publication reach or GPU/provider benchmarks from resume variants. Link the relevant repository as a new independent project or related public implementation.

The public portfolio still has explicit implementation gaps for production Ray/FSDP, large-model SFT/DPO, CARLA/ROS integration, real marketplace trials and provider-scale GPU/vLLM/Nebius measurements. The earlier Inference Systems Lab retains its separate small free-T4 arithmetic evidence. New toy workloads do not fill those gaps by relabeling results.

Each source's rights remain its own. Missing or inconsistent license information was handled by taking concepts only and writing new implementations. The MIT licenses cover the new project code and fictional fixtures.
