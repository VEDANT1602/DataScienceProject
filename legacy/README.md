# Earlier projects: the starting points behind the current work

My earlier projects explored language models, multimodal learning, computer vision and regression. I brought the original repositories from [Vedant160297](https://github.com/Vedant160297) into my current [VEDANT1602 portfolio](https://github.com/VEDANT1602/DataScienceProject) so the progression is visible in one place.

These are exact historical snapshots. I have kept the original notebooks, checkpoint files, embedded outputs, report, demonstration videos and attribution. They were inspected during migration, not executed or re-benchmarked. The newer projects elsewhere in this repository have separate tests and measured results.

## Start with the question each project explored

| Earlier project | Topic and approach visible in the source | What to understand before using it |
| --- | --- | --- |
| [LLM-Powered Knowledge Base](LLM-Powered-Knowledge-Base/) | Sentence embeddings and cosine similarity retrieve relevant context from a small illustrative knowledge base. | The included sample has four fictional product/fitness entries. It demonstrates retrieval, not an evaluated generative-answer service. |
| [Cryptocurrency Sentiment Analysis](Cryptocurrency-Sentiment-Analysis-System/) | A DistilBERT sequence-classification notebook builds a tokenization, training and evaluation pipeline. | Its default fixture contains eight synthetic statements. That fixture cannot establish real-market sentiment accuracy or a trading signal. |
| [Multimodal Heart Disease Prediction](Heart-Disease-Prediction-System/) | A PyTorch CNN extracts image embeddings, which are combined with tabular variables for XGBoost classification. | The expected CSV and patient-image data are not in the source repository. This is an illustrative pipeline, with no clinical-validation claim. |
| [FormVision](FormVision/) | OpenCV and MediaPipe notebooks use pose landmarks, joint angles and state transitions to count repetitions or describe movement. | Eight exercise notebooks and ten videos are preserved, including the original checkpoints. The rule-based movement demonstrations are not a clinical or biomechanics validation study. |
| [Used-car Price Prediction](Sales-Prediction-of-Cars-using-ML/) | A co-authored ASU report compares regression/tree methods, feature selection, PCA and training time across computing platforms. | This source repository contains the report rather than runnable code or its dataset. Divyesh Rathod, Meet Shah and Vedant Thaker are the report's credited authors. Its reported results were not rerun during this migration. |

## From relevance to a defensible answer

The knowledge-base notebook makes the first step concrete: embed the question, compare it with stored content, and return the closest passages. The engineering question that follows is whether the closest passage is an acceptable source for the person asking. Approval, validity dates, geographic scope and conflicting records all matter after relevance.

[Evidence Gate](../projects/evidence-gate/) examines those boundaries in a new, independently measured reference implementation. It has its own fictional corpus, explicit answer/clarify/abstain contract and regression suite. Its results belong to that new experiment, not to the older notebook.

## From a model pipeline to evidence that can survive review

The sentiment and multimodal notebooks show the structure of a learning workflow. The next question is what data, split and evaluation population would justify trusting its output. A small synthetic fixture or a missing private-data path is a useful implementation starting point, but it does not establish external validity.

The current [Point-in-time Risk](../projects/point-in-time-risk/) and [Temporal Recommendations](../projects/temporal-recommendations/) projects make their time boundaries, candidate sets, label availability and limitations explicit. They extend the engineering method; they do not retroactively validate the archived experiments.

## From a visible demonstration to a reproducible system

FormVision makes intermediate reasoning visible through landmarks, angles, counters and annotated frames. The used-car report compares model and computing choices rather than describing a single algorithm in isolation. Both are useful foundations for asking what should be measured, which alternative is fair, and where the result stops applying.

The used-car report credits its complete code reference to [the original co-authored project](https://github.com/mshah72/MachineLearningAndDeepLearning-Project). That external repository has not been silently relabeled as solo work or imported as an additional project from this source account.

## Verify the migration

The [migration manifest](migration-manifest.json) records all five source repositories, the exact source commits and trees, reachable commit metadata, refs, file sizes, Git blob identifiers and SHA-256 hashes. The migration exported tracked files directly from Git blobs, avoiding checkout line-ending changes. All 35 exported files match their recorded source blobs.

From the repository root, verify the committed snapshots without executing any notebook:

```bash
python legacy/verify_snapshots.py --git-objects
```

For an extracted download copy without Git metadata, use `python legacy/verify_snapshots.py`. Git-object mode avoids treating platform checkout line-ending conversions as source-history changes.

Original commit-history links remain available in each source repository:

- [Knowledge Base history](https://github.com/Vedant160297/LLM-Powered-Knowledge-Base/commits/main/)
- [Sentiment Analysis history](https://github.com/Vedant160297/Cryptocurrency-Sentiment-Analysis-System/commits/main/)
- [Multimodal Prediction history](https://github.com/Vedant160297/Heart-Disease-Prediction-System/commits/main/)
- [FormVision history](https://github.com/Vedant160297/FormVision/commits/main/)
- [Used-car Prediction history](https://github.com/Vedant160297/Sales-Prediction-of-Cars-using-ML/commits/main/)

## Attribution and data rights

The source repositories did not include standalone license files at the pinned commits. Their original code, embedded outputs, videos and co-authored report retain their existing rights and attribution; the portfolio's MIT license does not relicense these historical materials. Source assets were preserved, not cleaned or rewritten. The original authors and any third-party data or media terms continue to apply.
