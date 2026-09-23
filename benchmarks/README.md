# Accuracy benchmark v1

Run from the repository checkout (with Python requirements and Node installed):

```sh
python benchmarks/run.py --output benchmarks/results.json
npm test
python -m unittest discover tests -v
```

`cases.json` is a fixed, synthetic English dataset with character-span annotations, token-level positive labels, explicitly eligible token IDs, and expected percentages. It contains 3 development, 18 separate evaluation, and 4 challenge cases. No private manuscript or institutional source content is included. Do not tune matching parameters on evaluation/challenge cases: add future calibration examples to development, and collect a new independently annotated evaluation set before claiming generalization.

The two engines receive exactly the same source corpus, text, and exclusions. The Node benchmark overrides built-in sources; the Python benchmark disables online retrieval. This isolates matching correctness from corpus coverage and network availability. The runner fails on invalid annotations, denominator/accounting errors, or Python/Node coverage differences. CI compares the complete deterministic output with the committed baseline and uploads results; an intentional algorithm change requires reviewing and updating the baseline.

## Metrics

- Token precision: TP / (TP + FP); token recall: TP / (TP + FN).
- Token F1: 2TP / (2TP + FP + FN).
- Token false-positive rate: FP / (FP + TN).
- Passage recall: fraction of annotated eligible passages with at least 50% of their words recovered. This is **not** exact passage-boundary accuracy.
- Score MAE: mean absolute difference between predicted and expected scores, in percentage points.
- Undefined rates use JSON null, not an invented perfect score. Each case lists counts and its score error.

The evaluator has a hand-calculated regression test demonstrating that identical overall percentages can still conceal false positives and missed matches.

## Current results and interpretation

Both engines agree on all 25 fixtures. The 18 evaluation cases have token precision/recall 1.0 and score MAE 0.0. These are small constructed examples of exact overlap, exclusions, duplicated sources, source overlap, citation retention, case/punctuation normalization, and unrelated text. **This is a regression baseline, not a claim of 100% real-world accuracy or equivalence to SafeAssign.**

All four challenge cases expose limitations: a synonym paraphrase, a three-word copied fragment, a missing source, and generic boilerplate. Challenge token recall is 0.0 and score MAE is 85.72 percentage points. The boilerplate case is deliberately labeled as non-actionable common wording despite exact lexical overlap: its false positive measures a *review-policy* disagreement, not a failure to find identical words. Keep challenge results separate from exact lexical-coverage results.

For a credible production evaluation, collect consented documents with independently annotated source passages and include difficult negatives from the same subject area. Keep documents and source families disjoint between development and evaluation; have reviewers adjudicate uncertain labels. Measure retrieval coverage separately from matching quality. Add multilingual, OCR, long-document, and source-outage cases. A SafeAssign total alone supplies neither token ground truth nor access to its private corpus.
