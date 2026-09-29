# Writing-pattern score: threshold calibration

**Result: the existing `pattern_score` band thresholds (Elevated ≥ 25, High
≥ 65) were checked against 21 guaranteed-human documents and produced zero
false positives. No threshold was changed.** This is a validation result,
not a re-tuning: with only 21 documents there is no principled basis to
*loosen* the thresholds (more sensitive) without risking false positives
the sample is too small to have caught. See the honest limitation below
before treating this as more than a sanity check.

Methodology follows the MIT-licensed `avoid-ai-writing` project's own
approach: score a corpus of confirmed human writing, then report how many
of those documents the current thresholds would flag. See
[THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md).

## Corpus

21 documents, two registers, both **guaranteed human** because both
predate large language models entirely — see
[human_corpus/README.md](human_corpus/README.md) for exact sourcing:

- 10 excerpts from Ralph Waldo Emerson's *Essays: First Series* (1841, public domain)
- 11 full abstracts of well-known pre-November-2022 papers from arXiv (ML/NLP/physics)

Reproduce with:

```bash
python3 benchmarks/calibrate_thresholds.py
```

## Results

| Metric | Value |
|---|---|
| N | 21 |
| Mean `pattern_score` | 8.8 |
| Median | 7.4 |
| Max observed | 22.2 |
| p95 | 18.5 |
| Flagged Elevated+ (≥25) | **0 / 21 (0%)** |
| Flagged High (≥65) | 0 / 21 (0%) |

The highest score any human document reached was 22.2, against an Elevated
cutoff of 25 — a margin of about 2.8 points, or roughly 13% of the
threshold itself. Every category-level threshold in `core/ai_detector.py`
/ `lib/ai_detector.js` is unchanged.

### Which categories fire on real human writing

`specificity` (unanchored/vague claims) fired on 15 of 21 documents — by
far the most common source of nonzero score on genuine human prose, though
never enough by itself to cross into Elevated territory here. `burstiness`
fired on 8. Every other category fired on 5 or fewer. This is a concrete,
data-backed candidate for the next review pass: if the `specificity`
category is ever tightened or loosened, this corpus is the regression
check to run against it.

## Why the thresholds were not changed

`avoid-ai-writing` calibrated against 376 documents and could reason about
a specific false-positive rate (1.9% at their threshold). Twenty-one
documents is too small a sample to compute a trustworthy percentile for an
academic-integrity tool — a false "Elevated" flag directed at a real
student is costly, so the sample used to loosen a threshold needs to be
large enough that a rare human outlier isn't simply missing from it. This
run validates that 25 is not obviously wrong; it does not license tuning
it down toward the observed p95 (18.5) without more data.

## What would justify a change

Growing `human_corpus/` — more documents, more registers, and ideally some
real (permissioned) student writing so the sample matches the tool's
actual use case rather than 1841 prose and paper abstracts — to a size
where a specific target false-positive rate (for example, `avoid-ai-writing`'s
sub-2%) can be computed with a defensible confidence interval, the way
their 376-document corpus supports theirs.
