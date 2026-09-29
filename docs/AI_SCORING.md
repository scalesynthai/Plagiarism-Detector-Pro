# Explainable writing-pattern scoring

The writing-pattern score is a review aid, not a probability that AI wrote a
document. It scores nine visible signal groups from 0 to 3 and normalizes the
sum to 100:

1. Predictable vocabulary
2. Sentence rhythm
3. Hedge density
4. Formulaic structure
5. Specificity and grounding
6. Transition fingerprint
7. Punctuation fingerprint
8. Assistant-style register
9. Rhetorical scaffolding

Every non-zero category includes the phrases or sentence spans that caused the
finding and a focused revision suggestion. Samples under 120 words are marked
as limited because document-level rhythm and structure need enough text.

## Em dashes

The analyzer reports both the count and the number of em dashes per 300 words.
More than one per 300 words is highlighted for review. An em dash alone cannot
produce a high score or establish authorship. This preserves the professor's
useful style feedback without converting one punctuation choice into an
academic-integrity accusation.

## Evidence integrity

The evidence score is separate from the writing-pattern score. It combines the
available components and renormalizes their weights:

- recognized empirical claims with same-sentence citations: 50%
- in-text citations linked to bibliography entries: 30%
- source-type quality heuristic: 20%

Missing components do not become zero. Citation syntax and bibliography links
do not prove that a source exists or supports the sentence, so the report tells
the writer to verify each important claim against the cited source.

## Compatibility fields

`ai_probability` and `human_probability` remain in API and npm CLI output for
backward compatibility. They mirror the uncalibrated pattern score and its
complement and must not be described as calibrated probabilities.
